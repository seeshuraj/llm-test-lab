"""
RAG-specific metrics computed per scenario result.

Metrics:
  - faithfulness:        Does the answer stay within the context? (LLM judge, claim-level)
  - context_recall:      Does the context contain enough to answer the question? (embedding sim)
  - answer_relevance:    Is the answer on-topic for the question? (embedding cosine sim)
  - context_precision:   Is the retrieved context focused / not noisy? (LLM judge)

Accuracy improvements (v2):
  - Fixed: `expected` kwarg now accepted (was causing silent crash in main.py)
  - Fixed: output key renamed answer_relevancy → answer_relevance (consistent with main.py)
  - Faithfulness uses claim decomposition (RAGAS-style) not holistic prompt
  - Context recall uses `expected` answer when available for better signal
  - LLM judge prompts use step-by-step CoT before score (G-Eval style)
  - Verbosity bias mitigation: explicit anti-verbosity instruction in prompts
  - All scores clamped to [0, 1]

Each metric returns a float in [0.0, 1.0].
"""

from __future__ import annotations

import json
import re
from typing import Optional


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = sum(x ** 2 for x in a) ** 0.5
    mag_b = sum(x ** 2 for x in b) ** 0.5
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _get_embedder():
    """Lazy-load SentenceTransformer so it doesn't slow startup."""
    try:
        from sentence_transformers import SentenceTransformer
        # all-MiniLM-L6-v2: fast, good quality, 384-dim embeddings
        return SentenceTransformer("all-MiniLM-L6-v2")
    except ImportError:
        return None


_embedder = None


def _embed(text: str) -> Optional[list[float]]:
    global _embedder
    if _embedder is None:
        _embedder = _get_embedder()
    if _embedder is None:
        return None
    return _embedder.encode(text, normalize_embeddings=True).tolist()


# ---------------------------------------------------------------------------
# LLM-judge helpers
# ---------------------------------------------------------------------------

def _extract_score(text: str) -> Optional[float]:
    """Extract a numeric score from LLM JSON response."""
    try:
        match = re.search(r'\{[^}]*"score"\s*:\s*([0-9.]+)[^}]*\}', text)
        if match:
            return float(match.group(1))
        data = json.loads(text)
        return float(data.get("score", 0.5))
    except Exception:
        nums = re.findall(r"\b(0(?:\.\d+)?|1(?:\.0+)?)\b", text)
        return float(nums[0]) if nums else None


async def _llm_score(judge, prompt: str) -> float:
    """Call the Groq/Anthropic judge with a raw scoring prompt."""
    try:
        # Use _single_judge at temp=0 for determinism on RAG metrics
        result = await judge._single_judge(
            question="",
            context="",
            answer="",
            rubric=prompt,
            temperature=0.0,
        )
        return max(0.0, min(1.0, float(result.score)))
    except Exception:
        # Fallback to legacy judge() if _single_judge not available
        try:
            result = await judge.judge(
                question="",
                context="",
                answer="",
                rubric=prompt,
            )
            return max(0.0, min(1.0, float(result.score)))
        except Exception:
            return 0.5


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class RagScores:
    __slots__ = ("faithfulness", "context_recall", "answer_relevance", "context_precision")

    def __init__(
        self,
        faithfulness: float,
        context_recall: float,
        answer_relevance: float,
        context_precision: float,
    ):
        self.faithfulness = round(max(0.0, min(1.0, faithfulness)), 4)
        self.context_recall = round(max(0.0, min(1.0, context_recall)), 4)
        self.answer_relevance = round(max(0.0, min(1.0, answer_relevance)), 4)
        self.context_precision = round(max(0.0, min(1.0, context_precision)), 4)

    def to_dict(self) -> dict:
        return {
            "faithfulness": self.faithfulness,
            "context_recall": self.context_recall,
            "answer_relevance": self.answer_relevance,
            "context_precision": self.context_precision,
        }


# ---------------------------------------------------------------------------
# Metric implementations
# ---------------------------------------------------------------------------

async def _compute_faithfulness(judge, context: str, answer: str) -> float:
    """
    RAGAS-style faithfulness: decompose answer into atomic claims,
    then check each claim against context.

    Prompt uses CoT (G-Eval style) to reduce hallucinated scores.
    Anti-verbosity instruction prevents longer answers getting free points.
    """
    prompt = (
        "You are evaluating faithfulness: does the answer contain ONLY information "
        "supported by the context? Longer answers are NOT inherently better — "
        "extra ungrounded claims REDUCE the score.\n\n"
        f"## Context\n{context}\n\n"
        f"## Answer\n{answer}\n\n"
        "## Step-by-step instructions\n"
        "1. List every distinct factual claim made in the answer (max 10).\n"
        "2. For each claim, mark it as SUPPORTED or UNSUPPORTED by the context.\n"
        "3. Score = (number of SUPPORTED claims) / (total claims).\n"
        "4. If the answer makes no factual claims, score = 1.0.\n"
        "5. If the answer directly contradicts the context, score = 0.0.\n\n"
        'Respond ONLY with JSON: {"score": <float 0-1>, "reason": "<brief>"}'
    )
    return await _llm_score(judge, prompt)


async def _compute_context_precision(judge, question: str, context: str) -> float:
    """
    Context precision: is the retrieved context focused and relevant to the question?
    Penalises noisy / irrelevant context even if the answer is correct.
    """
    prompt = (
        "You are evaluating context precision: is the provided context focused and "
        "relevant to the question, with minimal noise or off-topic information?\n\n"
        f"## Question\n{question}\n\n"
        f"## Context\n{context}\n\n"
        "## Step-by-step instructions\n"
        "1. Identify sentences in the context that are directly useful for answering the question.\n"
        "2. Identify sentences that are irrelevant noise.\n"
        "3. Score = (useful sentences) / (total sentences). Round to 2 decimal places.\n"
        "4. If all context is relevant, score = 1.0. If none is relevant, score = 0.0.\n\n"
        'Respond ONLY with JSON: {"score": <float 0-1>, "reason": "<brief>"}'
    )
    return await _llm_score(judge, prompt)


def _compute_context_recall_embedding(
    context: str,
    question: str,
    expected: str,
) -> float:
    """
    Embedding-based context recall.
    When expected answer is available: measures how well the context covers the expected answer.
    When not: falls back to question-context similarity as a proxy.
    """
    reference = expected.strip() if expected and expected.strip() else question
    ctx_emb = _embed(context)
    ref_emb = _embed(reference)
    if ctx_emb is None or ref_emb is None:
        # No embedder available: return neutral
        return 0.5
    return _cosine_sim(ctx_emb, ref_emb)


def _compute_answer_relevance_embedding(question: str, answer: str) -> float:
    """
    Answer relevance: cosine similarity between question and answer embeddings.
    High relevance = answer directly addresses the question.
    """
    q_emb = _embed(question)
    a_emb = _embed(answer)
    if q_emb is None or a_emb is None:
        return 0.5
    return _cosine_sim(q_emb, a_emb)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def compute_rag_metrics(
    *,
    question: str,
    context: str,
    answer: str,
    judge,  # GroqJudgeClient or AnthropicJudgeClient instance
    expected: str = "",  # FIX: was missing — main.py passes this kwarg
) -> dict:
    """
    Compute all 4 RAG metrics for a single scenario result.
    Returns a plain dict (stored as JSON in rag_scores column).
    Falls back gracefully when embeddings or judge unavailable.
    """
    import asyncio

    # LLM-judge metrics run concurrently
    faithfulness_task = asyncio.create_task(
        _compute_faithfulness(judge, context, answer)
    )
    context_precision_task = asyncio.create_task(
        _compute_context_precision(judge, question, context)
    )

    # Embedding metrics are synchronous (CPU-bound)
    context_recall = _compute_context_recall_embedding(context, question, expected)
    answer_relevance = _compute_answer_relevance_embedding(question, answer)

    faithfulness = await faithfulness_task
    context_precision = await context_precision_task

    scores = RagScores(
        faithfulness=faithfulness,
        context_recall=context_recall,
        answer_relevance=answer_relevance,
        context_precision=context_precision,
    )
    return scores.to_dict()

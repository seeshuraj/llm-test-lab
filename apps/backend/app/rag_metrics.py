"""
RAG-specific metrics computed per scenario result.

Metrics:
  - faithfulness:        Does the answer stay within the context? (LLM judge)
  - context_recall:      Does the context contain enough to answer the question? (embedding similarity)
  - answer_relevancy:    Is the answer on-topic for the question? (embedding cosine similarity)
  - context_precision:   Is the retrieved context actually needed / not noisy? (LLM judge)

Each metric returns a float in [0.0, 1.0].
All four are returned together as a RagScores dict.
"""

from __future__ import annotations

import json
import re
from typing import Optional


# ---------------------------------------------------------------------------
# Embedding-based helpers
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
# LLM-judge-based helpers
# ---------------------------------------------------------------------------

def _extract_score_from_json(text: str) -> Optional[float]:
    """Extract a numeric score from LLM JSON response like {\"score\": 0.8}."""
    try:
        match = re.search(r'\{[^}]*"score"\s*:\s*([0-9.]+)[^}]*\}', text)
        if match:
            return float(match.group(1))
        data = json.loads(text)
        return float(data.get("score", 0.5))
    except Exception:
        # fallback: find first float in range [0,1]
        nums = re.findall(r'\b(0(?:\.\d+)?|1(?:\.0+)?)\b', text)
        return float(nums[0]) if nums else 0.5


async def _llm_score(judge, prompt: str) -> float:
    """Call the Groq judge with a scoring prompt, return float 0-1."""
    try:
        result = await judge.judge(
            question="",
            context="",
            answer="",
            rubric=prompt,
            _raw_prompt_override=prompt,
        )
        # GroqJudgeClient returns a JudgeResult with .score
        if hasattr(result, "score"):
            return max(0.0, min(1.0, float(result.score)))
        return _extract_score_from_json(str(result)) or 0.5
    except Exception:
        return 0.5


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class RagScores:
    __slots__ = ("faithfulness", "context_recall", "answer_relevancy", "context_precision")

    def __init__(
        self,
        faithfulness: float,
        context_recall: float,
        answer_relevancy: float,
        context_precision: float,
    ):
        self.faithfulness = round(faithfulness, 4)
        self.context_recall = round(context_recall, 4)
        self.answer_relevancy = round(answer_relevancy, 4)
        self.context_precision = round(context_precision, 4)

    def to_dict(self) -> dict:
        return {
            "faithfulness": self.faithfulness,
            "context_recall": self.context_recall,
            "answer_relevancy": self.answer_relevancy,
            "context_precision": self.context_precision,
        }


async def compute_rag_metrics(
    *,
    question: str,
    context: str,
    answer: str,
    judge,  # GroqJudgeClient instance
) -> RagScores:
    """
    Compute all 4 RAG metrics for a single scenario result.
    Falls back gracefully if embeddings unavailable.
    """

    # --- 1. Faithfulness (LLM judge) ---
    # Does the answer only use information from the context?
    faithfulness_prompt = (
        f"You are evaluating whether an AI answer is faithful to the provided context.\n\n"
        f"Context:\n{context}\n\n"
        f"Answer:\n{answer}\n\n"
        f"Rules:\n"
        f"- Score 1.0 if every claim in the answer is directly supported by the context.\n"
        f"- Score 0.5 if some claims are supported but others are from outside the context.\n"
        f"- Score 0.0 if the answer contradicts or ignores the context entirely.\n"
        f"Respond only with JSON: {{\"score\": <float 0-1>, \"reason\": \"...\"}}"
    )
    faithfulness = await _llm_score(judge, faithfulness_prompt)

    # --- 2. Context Recall (embedding similarity: context vs question) ---
    # Does the context actually contain information relevant to answer the question?
    context_recall: float
    q_emb = _embed(question)
    c_emb = _embed(context)
    if q_emb and c_emb:
        context_recall = max(0.0, min(1.0, _cosine_sim(q_emb, c_emb)))
    else:
        # fallback to LLM judge
        cr_prompt = (
            f"Question: {question}\n\nContext:\n{context}\n\n"
            f"Does the context contain sufficient information to answer the question?\n"
            f"Score 1.0 = fully sufficient, 0.5 = partial, 0.0 = irrelevant.\n"
            f"Respond only with JSON: {{\"score\": <float 0-1>}}"
        )
        context_recall = await _llm_score(judge, cr_prompt)

    # --- 3. Answer Relevancy (embedding similarity: answer vs question) ---
    # Is the answer actually answering the question asked?
    answer_relevancy: float
    a_emb = _embed(answer)
    if q_emb and a_emb:
        answer_relevancy = max(0.0, min(1.0, _cosine_sim(q_emb, a_emb)))
    else:
        ar_prompt = (
            f"Question: {question}\n\nAnswer:\n{answer}\n\n"
            f"Is the answer directly relevant to the question?\n"
            f"Score 1.0 = fully relevant, 0.5 = partially relevant, 0.0 = off-topic.\n"
            f"Respond only with JSON: {{\"score\": <float 0-1>}}"
        )
        answer_relevancy = await _llm_score(judge, ar_prompt)

    # --- 4. Context Precision (LLM judge) ---
    # Is the retrieved context focused and not noisy / padded with irrelevant info?
    cp_prompt = (
        f"Question: {question}\n\nContext:\n{context}\n\n"
        f"Evaluate how precise and focused the context is for answering the question.\n"
        f"Rules:\n"
        f"- Score 1.0 if every sentence in the context is relevant to the question.\n"
        f"- Score 0.5 if the context contains a mix of relevant and irrelevant content.\n"
        f"- Score 0.0 if the context is mostly noise or unrelated to the question.\n"
        f"Respond only with JSON: {{\"score\": <float 0-1>, \"reason\": \"...\"}}"
    )
    context_precision = await _llm_score(judge, cp_prompt)

    return RagScores(
        faithfulness=faithfulness,
        context_recall=context_recall,
        answer_relevancy=answer_relevancy,
        context_precision=context_precision,
    )

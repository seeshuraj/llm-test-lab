"""
RAG Metrics Engine for LLM Test Lab.

Scores a (question, context, answer) triple across four RAGAS-inspired metrics:

  1. faithfulness       — LLM judge: does the answer stay within context? (no hallucination)
  2. answer_relevancy   — embedding cosine sim: does the answer address the question?
  3. context_recall     — embedding cosine sim: does the context cover the question?
  4. context_precision  — LLM judge: is the context focused (low noise)?

All scores are floats in [0.0, 1.0]. The composite score is the arithmetic mean.

Embedding strategy
------------------
The module uses a lightweight embedding backend with the following priority:

  1. sentence-transformers (all-MiniLM-L6-v2)  — best quality, ~80MB model
  2. sklearn TF-IDF cosine similarity           — zero-download fallback

The backend is auto-detected at import time. No GPU required.

Usage
-----
    from llm_test_lab_core.rag_metrics import score_scenario
    from llm_test_lab_core.judge_factory import get_judge

    judge = get_judge("claude-3-5-haiku")
    result = await score_scenario(
        judge=judge,
        scenario=scenario,
        answer="The refund window is 30 days.",
        latency_ms=312.0,
        variant_id="v1",
    )
"""

from __future__ import annotations

import asyncio
import time
from typing import List, Optional

from .models import MetricScore, Scenario, ScenarioResult

# ---------------------------------------------------------------------------
# Embedding backend (auto-detect at import time)
# ---------------------------------------------------------------------------

_USE_SBERT = False
_sbert_model = None

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    _sbert_model = SentenceTransformer("all-MiniLM-L6-v2")
    _USE_SBERT = True
except ImportError:
    pass


def _cosine(a: list, b: list) -> float:
    """Cosine similarity, numpy or pure-python fallback."""
    try:
        import numpy as np
        a, b = np.array(a, dtype=float), np.array(b, dtype=float)
        denom = (np.linalg.norm(a) * np.linalg.norm(b))
        return float(np.dot(a, b) / denom) if denom else 0.0
    except ImportError:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x ** 2 for x in a) ** 0.5
        norm_b = sum(x ** 2 for x in b) ** 0.5
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def _embed(texts: List[str]) -> List[List[float]]:
    """Return embeddings for a list of texts."""
    if _USE_SBERT and _sbert_model:
        vecs = _sbert_model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]

    # TF-IDF fallback
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        vec = TfidfVectorizer().fit_transform(texts)
        return vec.toarray().tolist()
    except ImportError:
        pass

    # Last-resort: character bigram bag
    def _bigrams(text: str):
        t = text.lower()
        return {t[i:i+2] for i in range(len(t) - 1)}

    all_bg = sorted(set().union(*[_bigrams(t) for t in texts]))
    def _vec(text):
        bg = _bigrams(text)
        return [1.0 if b in bg else 0.0 for b in all_bg]
    return [_vec(t) for t in texts]


# ---------------------------------------------------------------------------
# Metric implementations
# ---------------------------------------------------------------------------

async def _score_faithfulness(
    judge,
    question: str,
    answer: str,
    context_docs: List[str],
) -> MetricScore:
    """
    Faithfulness: does the answer contain ONLY claims supported by the context?
    Low score = hallucination detected.
    """
    rubric = (
        "Score faithfulness: how well does the answer stay within the provided context? "
        "1.0 = every claim is directly supported. "
        "0.0 = answer contains significant hallucinations or unsupported claims. "
        "Penalise heavily for any claim not traceable to the context."
    )
    result = await judge.score(
        question=question,
        answer=answer,
        context_docs=context_docs,
        rubric=rubric,
    )
    return MetricScore(
        name="faithfulness",
        score=result["score"],
        reason=result.get("reason", ""),
        judge_model=result.get("judge_model", ""),
    )


async def _score_context_precision(
    judge,
    question: str,
    answer: str,
    context_docs: List[str],
) -> MetricScore:
    """
    Context Precision: is the retrieved context focused and relevant?
    Low score = noisy / irrelevant context chunks retrieved.
    """
    if not context_docs:
        return MetricScore(
            name="context_precision",
            score=0.0,
            reason="No context provided.",
        )

    rubric = (
        "Score context precision: how focused and relevant are the provided context documents "
        "to answering this specific question? "
        "1.0 = all context is tightly relevant, no noise. "
        "0.0 = context is completely irrelevant or retrieved the wrong documents. "
        "Consider whether each context chunk contributes to answering the question."
    )
    result = await judge.score(
        question=question,
        answer=answer,
        context_docs=context_docs,
        rubric=rubric,
    )
    return MetricScore(
        name="context_precision",
        score=result["score"],
        reason=result.get("reason", ""),
        judge_model=result.get("judge_model", ""),
    )


def _score_answer_relevancy(
    question: str,
    answer: str,
) -> MetricScore:
    """
    Answer Relevancy: does the answer semantically address the question?
    Computed via embedding cosine similarity — no LLM call needed.
    """
    if not answer.strip():
        return MetricScore(
            name="answer_relevancy",
            score=0.0,
            reason="Empty answer.",
        )

    vecs = _embed([question, answer])
    sim = _cosine(vecs[0], vecs[1])
    # Cosine sim on short texts can be negative; clamp to [0, 1]
    score = max(0.0, min(1.0, sim))
    return MetricScore(
        name="answer_relevancy",
        score=round(score, 4),
        reason=f"Embedding cosine similarity: {score:.4f}",
        judge_model="embedding:all-MiniLM-L6-v2" if _USE_SBERT else "embedding:tfidf-fallback",
    )


def _score_context_recall(
    question: str,
    context_docs: List[str],
) -> MetricScore:
    """
    Context Recall: does the context contain enough information to answer the question?
    Computed as max cosine similarity between question and any context chunk.
    """
    if not context_docs:
        return MetricScore(
            name="context_recall",
            score=0.0,
            reason="No context provided.",
        )

    texts = [question] + context_docs
    vecs = _embed(texts)
    q_vec = vecs[0]
    sims = [_cosine(q_vec, vecs[i + 1]) for i in range(len(context_docs))]
    best = max(sims)
    score = max(0.0, min(1.0, best))
    return MetricScore(
        name="context_recall",
        score=round(score, 4),
        reason=f"Best chunk cosine similarity: {score:.4f} ({len(context_docs)} chunk(s))",
        judge_model="embedding:all-MiniLM-L6-v2" if _USE_SBERT else "embedding:tfidf-fallback",
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def score_scenario(
    judge,
    scenario: Scenario,
    answer: str,
    variant_id: str,
    latency_ms: float = 0.0,
    skip_metrics: Optional[List[str]] = None,
) -> ScenarioResult:
    """
    Score a single (scenario, answer) pair across all four RAG metrics.

    Args:
        judge:        Any JudgeClient from judge_factory.get_judge()
        scenario:     The Scenario being evaluated
        answer:       The LLM answer to score
        variant_id:   Which RAG variant produced this answer
        latency_ms:   Round-trip latency of the LLM call (optional)
        skip_metrics: List of metric names to skip, e.g. ["context_precision"]

    Returns:
        ScenarioResult with composite score + all four individual MetricScores
    """
    skip = set(skip_metrics or [])

    # --- Embedding-based metrics (sync, no I/O) ---
    answer_relevancy = (
        None if "answer_relevancy" in skip
        else _score_answer_relevancy(scenario.question, answer)
    )
    context_recall = (
        None if "context_recall" in skip
        else _score_context_recall(scenario.question, scenario.context_docs)
    )

    # --- LLM judge metrics (async, run concurrently) ---
    faithfulness_coro = (
        _score_faithfulness(judge, scenario.question, answer, scenario.context_docs)
        if "faithfulness" not in skip
        else _noop_metric("faithfulness")
    )
    context_precision_coro = (
        _score_context_precision(judge, scenario.question, answer, scenario.context_docs)
        if "context_precision" not in skip
        else _noop_metric("context_precision")
    )

    faithfulness, context_precision = await asyncio.gather(
        faithfulness_coro,
        context_precision_coro,
    )

    # --- Composite score: mean of all active metrics ---
    active = [
        m for m in [faithfulness, answer_relevancy, context_recall, context_precision]
        if m is not None
    ]
    composite = sum(m.score for m in active) / len(active) if active else 0.0

    # --- Primary reason: from faithfulness judge (most informative) ---
    reason = (
        faithfulness.reason if faithfulness
        else (answer_relevancy.reason if answer_relevancy else "")
    )
    judge_model = (
        faithfulness.judge_model if faithfulness
        else ""
    )

    return ScenarioResult(
        scenario_id=scenario.id,
        variant_id=variant_id,
        score=round(composite, 4),
        reason=reason,
        latency_ms=latency_ms,
        judge_model=judge_model,
        faithfulness=faithfulness,
        answer_relevancy=answer_relevancy,
        context_recall=context_recall,
        context_precision=context_precision,
        answer=answer,
    )


async def _noop_metric(name: str) -> None:
    """Skipped metric placeholder."""
    return None


# ---------------------------------------------------------------------------
# Batch scoring
# ---------------------------------------------------------------------------

async def score_all(
    judge,
    scenarios: List[Scenario],
    answers: List[str],
    variant_id: str,
    latency_ms_list: Optional[List[float]] = None,
    skip_metrics: Optional[List[str]] = None,
    concurrency: int = 5,
) -> List[ScenarioResult]:
    """
    Score multiple scenarios concurrently with a semaphore to avoid rate limits.

    Args:
        judge:           JudgeClient instance
        scenarios:       List of Scenario objects
        answers:         Corresponding LLM answers (same length as scenarios)
        variant_id:      Which RAG variant produced these answers
        latency_ms_list: Per-scenario latencies (optional)
        skip_metrics:    Metric names to skip for all scenarios
        concurrency:     Max simultaneous judge calls (default 5)

    Returns:
        List of ScenarioResult in the same order as input scenarios
    """
    if len(scenarios) != len(answers):
        raise ValueError(
            f"scenarios ({len(scenarios)}) and answers ({len(answers)}) must have equal length"
        )

    latencies = latency_ms_list or [0.0] * len(scenarios)
    sem = asyncio.Semaphore(concurrency)

    async def _bounded(scenario, answer, latency):
        async with sem:
            return await score_scenario(
                judge=judge,
                scenario=scenario,
                answer=answer,
                variant_id=variant_id,
                latency_ms=latency,
                skip_metrics=skip_metrics,
            )

    return await asyncio.gather(
        *[_bounded(s, a, l) for s, a, l in zip(scenarios, answers, latencies)]
    )

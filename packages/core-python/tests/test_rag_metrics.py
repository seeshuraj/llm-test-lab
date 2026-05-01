"""
Unit tests for rag_metrics.py.

Runs fully offline — uses a mock judge that returns deterministic scores.
No API keys needed.
"""

import asyncio
import pytest
from llm_test_lab_core.models import Scenario
from llm_test_lab_core.rag_metrics import (
    score_scenario,
    score_all,
    _score_answer_relevancy,
    _score_context_recall,
)


# ---------------------------------------------------------------------------
# Mock judge
# ---------------------------------------------------------------------------

class MockJudge:
    """Deterministic judge returning a fixed score for all calls."""

    def __init__(self, score: float = 0.9, reason: str = "mock"):
        self._score = score
        self._reason = reason

    async def score(self, question, answer, context_docs, rubric, **kwargs):
        return {
            "score": self._score,
            "reason": self._reason,
            "judge_model": "mock:judge",
            "raw": "",
        }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SCENARIO = Scenario(
    id="s1",
    question="What is the refund policy?",
    context_docs=["Customers may request a refund within 30 days of purchase."],
    expected_answer="Refunds are available within 30 days.",
)

ANSWER = "Refunds are available within 30 days of purchase."


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_answer_relevancy_high():
    metric = _score_answer_relevancy(
        question="What is the refund policy?",
        answer="Refunds are available within 30 days.",
    )
    assert metric.name == "answer_relevancy"
    assert 0.0 <= metric.score <= 1.0
    # Same-domain texts should score reasonably high
    assert metric.score > 0.2


def test_answer_relevancy_empty():
    metric = _score_answer_relevancy(question="What?", answer="")
    assert metric.score == 0.0


def test_context_recall_with_context():
    metric = _score_context_recall(
        question="What is the refund policy?",
        context_docs=["Customers may request a refund within 30 days."],
    )
    assert metric.name == "context_recall"
    assert 0.0 <= metric.score <= 1.0
    assert metric.score > 0.1


def test_context_recall_no_context():
    metric = _score_context_recall(question="What?", context_docs=[])
    assert metric.score == 0.0


def test_score_scenario_composite():
    judge = MockJudge(score=0.8)
    result = asyncio.run(score_scenario(
        judge=judge,
        scenario=SCENARIO,
        answer=ANSWER,
        variant_id="v1",
        latency_ms=100.0,
    ))
    # Composite = mean of 4 metrics; LLM metrics = 0.8, embedding metrics vary
    assert 0.0 <= result.score <= 1.0
    assert result.scenario_id == "s1"
    assert result.variant_id == "v1"
    assert result.faithfulness is not None
    assert result.answer_relevancy is not None
    assert result.context_recall is not None
    assert result.context_precision is not None
    assert result.latency_ms == 100.0
    assert result.answer == ANSWER


def test_score_scenario_skip_metrics():
    judge = MockJudge(score=1.0)
    result = asyncio.run(score_scenario(
        judge=judge,
        scenario=SCENARIO,
        answer=ANSWER,
        variant_id="v1",
        skip_metrics=["context_precision", "context_recall"],
    ))
    assert result.context_precision is None
    assert result.context_recall is None
    assert result.faithfulness is not None
    assert result.answer_relevancy is not None


def test_score_all_batch():
    judge = MockJudge(score=0.75)
    scenarios = [SCENARIO, SCENARIO]
    answers = [ANSWER, ANSWER]
    results = asyncio.run(score_all(
        judge=judge,
        scenarios=scenarios,
        answers=answers,
        variant_id="v1",
        concurrency=2,
    ))
    assert len(results) == 2
    for r in results:
        assert 0.0 <= r.score <= 1.0


def test_score_all_length_mismatch():
    judge = MockJudge()
    with pytest.raises(ValueError, match="equal length"):
        asyncio.run(score_all(
            judge=judge,
            scenarios=[SCENARIO],
            answers=[],
            variant_id="v1",
        ))

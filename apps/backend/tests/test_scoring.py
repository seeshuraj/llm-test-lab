"""
Unit tests for scoring helpers — no network calls, no DB.
Tests: cosine similarity, JSON score extraction, RagScores dataclass.
"""
import pytest
import sys
import os
import json
import math

# ---------------------------------------------------------------------------
# Inline minimal implementations so tests run without the full backend stack
# (mirrors what rag_metrics.py does under the hood)
# ---------------------------------------------------------------------------

def _cosine_sim(a: list, b: list) -> float:
    """Cosine similarity between two equal-length float vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


def _extract_score_from_json(raw: str) -> float:
    """Extract a 0-1 score from LLM judge JSON, with regex fallback."""
    import re
    try:
        data = json.loads(raw)
        val = data.get("score", 0.0)
        return max(0.0, min(1.0, float(val)))
    except Exception:
        match = re.search(r"[0-9]+(?:\.[0-9]+)?", raw)
        if match:
            return max(0.0, min(1.0, float(match.group())))
        return 0.0


from dataclasses import dataclass

@dataclass
class RagScores:
    faithfulness: float
    context_recall: float
    answer_relevancy: float
    context_precision: float

    def to_dict(self) -> dict:
        return {
            "faithfulness": round(self.faithfulness, 4),
            "context_recall": round(self.context_recall, 4),
            "answer_relevancy": round(self.answer_relevancy, 4),
            "context_precision": round(self.context_precision, 4),
        }


# ---------------------------------------------------------------------------
# Tests: cosine similarity
# ---------------------------------------------------------------------------

class TestCosineSim:
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        assert _cosine_sim(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert _cosine_sim([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_zero_vector_returns_zero(self):
        assert _cosine_sim([0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_antiparallel_vectors(self):
        assert _cosine_sim([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_partial_similarity(self):
        score = _cosine_sim([1.0, 1.0, 0.0], [1.0, 0.0, 0.0])
        assert 0.0 < score < 1.0

    def test_mismatched_lengths_returns_zero(self):
        assert _cosine_sim([1.0, 0.0], [1.0]) == 0.0

    def test_empty_vector_returns_zero(self):
        assert _cosine_sim([], []) == 0.0


# ---------------------------------------------------------------------------
# Tests: JSON score extraction
# ---------------------------------------------------------------------------

class TestExtractScore:
    def test_clean_json_object(self):
        assert _extract_score_from_json('{"score": 0.85, "reason": "good"}') == pytest.approx(0.85)

    def test_clamps_above_one(self):
        assert _extract_score_from_json('{"score": 1.5}') == pytest.approx(1.0)

    def test_clamps_below_zero(self):
        assert _extract_score_from_json('{"score": -0.2}') == pytest.approx(0.0)

    def test_regex_fallback_on_prose(self):
        score = _extract_score_from_json("The answer scores approximately 0.72 out of 1.0")
        assert score == pytest.approx(0.72)

    def test_malformed_json_fallback(self):
        score = _extract_score_from_json("{score: 0.6}")
        assert 0.0 <= score <= 1.0

    def test_no_number_returns_zero(self):
        assert _extract_score_from_json("no numbers here at all") == 0.0

    def test_integer_score(self):
        assert _extract_score_from_json('{"score": 1}') == pytest.approx(1.0)

    def test_zero_score(self):
        assert _extract_score_from_json('{"score": 0}') == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Tests: RagScores dataclass
# ---------------------------------------------------------------------------

class TestRagScores:
    def test_to_dict_keys(self):
        s = RagScores(faithfulness=0.9, context_recall=0.8, answer_relevancy=0.75, context_precision=0.6)
        d = s.to_dict()
        assert set(d.keys()) == {"faithfulness", "context_recall", "answer_relevancy", "context_precision"}

    def test_to_dict_values(self):
        s = RagScores(faithfulness=0.9, context_recall=0.8, answer_relevancy=0.75, context_precision=0.6)
        d = s.to_dict()
        assert d["faithfulness"] == pytest.approx(0.9)
        assert d["context_recall"] == pytest.approx(0.8)

    def test_to_dict_rounding(self):
        s = RagScores(faithfulness=0.333333, context_recall=0.666666, answer_relevancy=0.0, context_precision=1.0)
        d = s.to_dict()
        assert d["faithfulness"] == pytest.approx(0.3333, abs=0.0001)
        assert d["context_recall"] == pytest.approx(0.6667, abs=0.0001)

    def test_perfect_scores(self):
        s = RagScores(faithfulness=1.0, context_recall=1.0, answer_relevancy=1.0, context_precision=1.0)
        d = s.to_dict()
        assert all(v == 1.0 for v in d.values())

    def test_zero_scores(self):
        s = RagScores(faithfulness=0.0, context_recall=0.0, answer_relevancy=0.0, context_precision=0.0)
        d = s.to_dict()
        assert all(v == 0.0 for v in d.values())

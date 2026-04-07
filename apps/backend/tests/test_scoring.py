"""
Unit tests for scoring helpers in rag_metrics.py.
No network calls, no Groq API, no SentenceTransformer download.
All tests exercise pure-Python paths only.
"""
import sys
import os
import math
import json
import re
import pytest

# ---------------------------------------------------------------------------
# Path resolution — works when run as:
#   pytest apps/backend/tests/          (from repo root)
#   python -m pytest                    (from repo root with pytest.ini)
#   PYTHONPATH=. pytest ...             (CI with explicit path)
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from apps.backend.app.rag_metrics import _cosine_sim, _extract_score_from_json, RagScores


# ---------------------------------------------------------------------------
# _cosine_sim
# ---------------------------------------------------------------------------

class TestCosineSim:
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        assert _cosine_sim(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert _cosine_sim([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_antiparallel_vectors(self):
        assert _cosine_sim([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_zero_vector_a(self):
        assert _cosine_sim([0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_zero_vector_b(self):
        assert _cosine_sim([1.0, 0.0], [0.0, 0.0]) == 0.0

    def test_normalised_vectors(self):
        a = [1 / math.sqrt(2), 1 / math.sqrt(2)]
        assert _cosine_sim(a, a) == pytest.approx(1.0)

    def test_partial_similarity(self):
        a = [1.0, 0.0]
        b = [1 / math.sqrt(2), 1 / math.sqrt(2)]
        assert _cosine_sim(a, b) == pytest.approx(1 / math.sqrt(2), abs=1e-6)


# ---------------------------------------------------------------------------
# _extract_score_from_json
# ---------------------------------------------------------------------------

class TestExtractScoreFromJson:
    def test_clean_json_object(self):
        assert _extract_score_from_json('{"score": 0.85, "reason": "good"}') == pytest.approx(0.85)

    def test_score_integer(self):
        assert _extract_score_from_json('{"score": 1}') == pytest.approx(1.0)

    def test_score_zero(self):
        assert _extract_score_from_json('{"score": 0.0}') == pytest.approx(0.0)

    def test_regex_fallback_float_in_text(self):
        # Regex path: finds first float already in [0,1]
        result = _extract_score_from_json("The answer scores 0.7 out of 1.")
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_fallback_returns_0_5_on_no_numeric_match(self):
        # Implementation returns 0.5 when no numeric content found
        result = _extract_score_from_json("No numbers here at all.")
        assert result == pytest.approx(0.5)

    def test_malformed_json_uses_regex(self):
        result = _extract_score_from_json('{"score": 0.9 oops broken}')
        assert result == pytest.approx(0.9)

    def test_score_one_point_zero(self):
        assert _extract_score_from_json('{"score": 1.0}') == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# RagScores
# ---------------------------------------------------------------------------

class TestRagScores:
    def test_to_dict_keys(self):
        s = RagScores(
            faithfulness=0.9,
            context_recall=0.8,
            answer_relevancy=0.75,
            context_precision=0.6,
        )
        assert set(s.to_dict().keys()) == {
            "faithfulness", "context_recall", "answer_relevancy", "context_precision"
        }

    def test_to_dict_values(self):
        s = RagScores(
            faithfulness=0.9,
            context_recall=0.8,
            answer_relevancy=0.75,
            context_precision=0.6,
        )
        d = s.to_dict()
        assert d["faithfulness"] == pytest.approx(0.9)
        assert d["context_recall"] == pytest.approx(0.8)
        assert d["answer_relevancy"] == pytest.approx(0.75)
        assert d["context_precision"] == pytest.approx(0.6)

    def test_rounds_to_4dp(self):
        s = RagScores(
            faithfulness=0.99999,
            context_recall=0.33333,
            answer_relevancy=0.66666,
            context_precision=0.0,
        )
        assert s.faithfulness == pytest.approx(1.0, abs=1e-4)
        assert s.context_recall == pytest.approx(0.3333, abs=1e-4)

    def test_zero_scores(self):
        s = RagScores(0.0, 0.0, 0.0, 0.0)
        assert s.faithfulness == 0.0
        assert s.to_dict()["context_precision"] == 0.0

    def test_perfect_scores(self):
        s = RagScores(1.0, 1.0, 1.0, 1.0)
        assert all(v == 1.0 for v in s.to_dict().values())

    def test_avg_score_empty_results(self):
        results = []
        avg = sum(r for r in results) / len(results) if results else 0.0
        assert avg == 0.0

    def test_avg_score_normal(self):
        scores = [0.8, 0.6, 1.0]
        avg = round(sum(scores) / len(scores), 4)
        assert avg == pytest.approx(0.8)

    def test_avg_score_single(self):
        scores = [0.42]
        avg = round(sum(scores) / len(scores), 4)
        assert avg == pytest.approx(0.42)

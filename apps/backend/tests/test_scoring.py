"""
Unit tests for scoring helpers in rag_metrics.py.
No network calls, no Groq/Groq API, no SentenceTransformer download.
All tests exercise pure-Python paths only.
"""
import sys
import os
import importlib
import pytest

# ---------------------------------------------------------------------------
# Resolve the package path regardless of cwd or pytest invocation style.
# Works when run as:
#   pytest apps/backend/tests/          (from repo root)
#   python -m pytest                    (from repo root with pytest.ini)
# ---------------------------------------------------------------------------
_BACKEND_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..")
sys.path.insert(0, os.path.abspath(_BACKEND_ROOT))

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
        # opposite direction → cosine = -1.0
        assert _cosine_sim([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_zero_vector_a(self):
        # zero magnitude → safe return 0.0 (no ZeroDivisionError)
        assert _cosine_sim([0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_zero_vector_b(self):
        assert _cosine_sim([1.0, 0.0], [0.0, 0.0]) == 0.0

    def test_normalised_vectors_similarity(self):
        import math
        a = [1 / math.sqrt(2), 1 / math.sqrt(2)]
        b = [1 / math.sqrt(2), 1 / math.sqrt(2)]
        assert _cosine_sim(a, b) == pytest.approx(1.0)

    def test_partial_similarity(self):
        # 45-degree angle → cosine = sqrt(2)/2 ≈ 0.707
        import math
        a = [1.0, 0.0]
        b = [1 / math.sqrt(2), 1 / math.sqrt(2)]
        assert _cosine_sim(a, b) == pytest.approx(1 / math.sqrt(2), abs=1e-6)


# ---------------------------------------------------------------------------
# _extract_score_from_json
# ---------------------------------------------------------------------------

class TestExtractScoreFromJson:
    def test_clean_json_object(self):
        assert _extract_score_from_json('{"score": 0.85, "reason": "good"}') == pytest.approx(0.85)

    def test_score_integer_in_json(self):
        assert _extract_score_from_json('{"score": 1}') == pytest.approx(1.0)

    def test_score_zero(self):
        assert _extract_score_from_json('{"score": 0.0}') == pytest.approx(0.0)

    def test_regex_fallback_plain_text(self):
        # no JSON — should find the first float in [0,1]
        result = _extract_score_from_json("The answer scores approximately 0.7 out of 1.")
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_regex_fallback_returns_0_5_on_no_match(self):
        # no numeric content — fallback default is 0.5
        result = _extract_score_from_json("No numbers here at all.")
        assert result == pytest.approx(0.5)

    def test_malformed_json_uses_regex(self):
        # malformed JSON — regex rescues it
        result = _extract_score_from_json('{"score": 0.9 oops broken}')
        assert result == pytest.approx(0.9)


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
        d = s.to_dict()
        assert set(d.keys()) == {"faithfulness", "context_recall", "answer_relevancy", "context_precision"}

    def test_to_dict_values(self):
        s = RagScores(
            faithfulness=0.9,
            context_recall=0.8,
            answer_relevancy=0.75,
            context_precision=0.6,
        )
        assert s.to_dict()["faithfulness"] == pytest.approx(0.9)
        assert s.to_dict()["context_recall"] == pytest.approx(0.8)

    def test_rounding_to_4dp(self):
        s = RagScores(
            faithfulness=0.99999,
            context_recall=0.33333,
            answer_relevancy=0.66666,
            context_precision=0.0,
        )
        # round() to 4dp
        assert s.faithfulness == pytest.approx(1.0, abs=1e-4)
        assert s.context_recall == pytest.approx(0.3333, abs=1e-4)

    def test_zero_scores(self):
        s = RagScores(
            faithfulness=0.0,
            context_recall=0.0,
            answer_relevancy=0.0,
            context_precision=0.0,
        )
        assert s.faithfulness == 0.0
        assert s.to_dict()["context_precision"] == 0.0

    def test_perfect_scores(self):
        s = RagScores(
            faithfulness=1.0,
            context_recall=1.0,
            answer_relevancy=1.0,
            context_precision=1.0,
        )
        assert all(v == 1.0 for v in s.to_dict().values())

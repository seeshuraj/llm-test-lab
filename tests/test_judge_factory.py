"""Unit tests for judge_factory — covers all four judge strategies."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

SAMPLE_SCENARIO = {
    "id": "s1",
    "question": "What is the capital of France?",
    "context_docs": ["France is a country in Western Europe. Its capital city is Paris."],
    "expected_keywords": ["Paris"],
}

SAMPLE_ANSWER = "The capital of France is Paris."


# ---------------------------------------------------------------------------
# Keyword judge
# ---------------------------------------------------------------------------

class TestKeywordJudge:
    """Tests for the keyword-matching judge strategy."""

    def _make_judge(self):
        from apps.backend.app.judge_factory import keyword_judge
        return keyword_judge

    def test_all_keywords_present(self):
        from apps.backend.app.judge_factory import keyword_judge
        result = keyword_judge(
            question=SAMPLE_SCENARIO["question"],
            context_docs=SAMPLE_SCENARIO["context_docs"],
            answer=SAMPLE_ANSWER,
            expected_keywords=["Paris"],
        )
        assert result["score"] >= 0.8
        assert "Paris" in result["reason"] or "keyword" in result["reason"].lower()

    def test_no_keywords_match(self):
        from apps.backend.app.judge_factory import keyword_judge
        result = keyword_judge(
            question="What is the capital of France?",
            context_docs=["No relevant info here."],
            answer="I do not know.",
            expected_keywords=["Paris"],
        )
        assert result["score"] < 0.5

    def test_partial_keywords(self):
        from apps.backend.app.judge_factory import keyword_judge
        result = keyword_judge(
            question="Name two cities in France.",
            context_docs=["Paris and Lyon are major French cities."],
            answer="Paris is a city.",
            expected_keywords=["Paris", "Lyon"],
        )
        # score should be between 0 and 1 (not full pass, not full fail)
        assert 0.0 < result["score"] < 1.0

    def test_empty_keywords_defaults_to_mid_score(self):
        from apps.backend.app.judge_factory import keyword_judge
        result = keyword_judge(
            question="Tell me something.",
            context_docs=["Some context."],
            answer="Some answer.",
            expected_keywords=[],
        )
        # No keywords means we cannot assert much; just ensure it returns a valid score
        assert 0.0 <= result["score"] <= 1.0
        assert "reason" in result

    def test_case_insensitive_matching(self):
        from apps.backend.app.judge_factory import keyword_judge
        result = keyword_judge(
            question="Capital?",
            context_docs=["Paris is the capital."],
            answer="the capital is paris.",
            expected_keywords=["PARIS"],
        )
        assert result["score"] >= 0.8


# ---------------------------------------------------------------------------
# Semantic judge
# ---------------------------------------------------------------------------

class TestSemanticJudge:
    """Tests for the cosine-similarity / semantic judge strategy."""

    @patch("apps.backend.app.judge_factory.compute_similarity", return_value=0.92)
    def test_high_similarity_passes(self, mock_sim):
        from apps.backend.app.judge_factory import semantic_judge
        result = semantic_judge(
            question=SAMPLE_SCENARIO["question"],
            context_docs=SAMPLE_SCENARIO["context_docs"],
            answer=SAMPLE_ANSWER,
            expected_keywords=SAMPLE_SCENARIO["expected_keywords"],
        )
        assert result["score"] >= 0.8
        mock_sim.assert_called_once()

    @patch("apps.backend.app.judge_factory.compute_similarity", return_value=0.18)
    def test_low_similarity_fails(self, mock_sim):
        from apps.backend.app.judge_factory import semantic_judge
        result = semantic_judge(
            question="What is 2+2?",
            context_docs=["The Eiffel Tower is tall."],
            answer="Bananas are yellow.",
            expected_keywords=[],
        )
        assert result["score"] < 0.5

    @patch("apps.backend.app.judge_factory.compute_similarity", return_value=0.62)
    def test_mid_similarity_is_warn(self, mock_sim):
        from apps.backend.app.judge_factory import semantic_judge
        result = semantic_judge(
            question="Where is the Eiffel Tower?",
            context_docs=["The Eiffel Tower is in Paris, France."],
            answer="France has a famous tower.",
            expected_keywords=[],
        )
        assert 0.5 <= result["score"] < 0.8

    @patch(
        "apps.backend.app.judge_factory.compute_similarity",
        side_effect=RuntimeError("model not found"),
    )
    def test_similarity_error_returns_fallback(self, mock_sim):
        """If the embedding model errors, the judge should not crash."""
        from apps.backend.app.judge_factory import semantic_judge
        result = semantic_judge(
            question="Q",
            context_docs=["C"],
            answer="A",
            expected_keywords=[],
        )
        # Falls back gracefully
        assert 0.0 <= result["score"] <= 1.0
        assert "reason" in result


# ---------------------------------------------------------------------------
# Groq LLM judge
# ---------------------------------------------------------------------------

class TestGroqJudge:
    """Tests for the Groq-backed LLM judge."""

    @patch("apps.backend.app.judge_factory.groq_client")
    def test_groq_parses_score(self, mock_groq):
        """LLM returns a valid score JSON — judge parses it correctly."""
        from apps.backend.app.judge_factory import groq_judge

        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"score": 0.95, "reason": "Correct and well-grounded."}'
        mock_groq.chat.completions.create.return_value = mock_response

        result = groq_judge(
            question=SAMPLE_SCENARIO["question"],
            context_docs=SAMPLE_SCENARIO["context_docs"],
            answer=SAMPLE_ANSWER,
            expected_keywords=SAMPLE_SCENARIO["expected_keywords"],
            model="llama-3.1-8b-instant",
            rubric=None,
        )
        assert result["score"] == pytest.approx(0.95)
        assert "Correct" in result["reason"]

    @patch("apps.backend.app.judge_factory.groq_client")
    def test_groq_handles_malformed_json(self, mock_groq):
        """If LLM returns non-JSON, judge degrades gracefully."""
        from apps.backend.app.judge_factory import groq_judge

        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Sorry, I cannot score this."
        mock_groq.chat.completions.create.return_value = mock_response

        result = groq_judge(
            question="Q",
            context_docs=["C"],
            answer="A",
            expected_keywords=[],
            model="llama-3.1-8b-instant",
            rubric=None,
        )
        assert 0.0 <= result["score"] <= 1.0
        assert "reason" in result

    @patch("apps.backend.app.judge_factory.groq_client")
    def test_groq_score_clamped(self, mock_groq):
        """Scores outside [0, 1] from LLM are clamped."""
        from apps.backend.app.judge_factory import groq_judge

        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"score": 1.8, "reason": "Over the top."}'
        mock_groq.chat.completions.create.return_value = mock_response

        result = groq_judge(
            question="Q",
            context_docs=["C"],
            answer="A",
            expected_keywords=[],
            model="llama-3.1-8b-instant",
            rubric=None,
        )
        assert result["score"] <= 1.0

    @patch("apps.backend.app.judge_factory.groq_client")
    def test_groq_applies_custom_rubric(self, mock_groq):
        """Custom rubric text is included in the prompt sent to Groq."""
        from apps.backend.app.judge_factory import groq_judge

        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"score": 0.7, "reason": "Partial."}'
        mock_groq.chat.completions.create.return_value = mock_response

        custom_rubric = "Only pass if the word 'Paris' appears verbatim."
        groq_judge(
            question="Q",
            context_docs=["C"],
            answer="A",
            expected_keywords=[],
            model="llama-3.1-8b-instant",
            rubric=custom_rubric,
        )
        call_args = mock_groq.chat.completions.create.call_args
        prompt_text = str(call_args)
        assert custom_rubric in prompt_text

    @patch(
        "apps.backend.app.judge_factory.groq_client",
        side_effect=Exception("API timeout"),
    )
    def test_groq_api_error_returns_fallback(self, mock_groq):
        from apps.backend.app.judge_factory import groq_judge

        result = groq_judge(
            question="Q",
            context_docs=["C"],
            answer="A",
            expected_keywords=[],
            model="llama-3.1-8b-instant",
            rubric=None,
        )
        assert 0.0 <= result["score"] <= 1.0
        assert "reason" in result


# ---------------------------------------------------------------------------
# OpenAI LLM judge
# ---------------------------------------------------------------------------

class TestOpenAIJudge:
    """Tests for the OpenAI-backed LLM judge."""

    @patch("apps.backend.app.judge_factory.openai_client")
    def test_openai_parses_score(self, mock_openai):
        from apps.backend.app.judge_factory import openai_judge

        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"score": 0.88, "reason": "Good answer."}'
        mock_openai.chat.completions.create.return_value = mock_response

        result = openai_judge(
            question=SAMPLE_SCENARIO["question"],
            context_docs=SAMPLE_SCENARIO["context_docs"],
            answer=SAMPLE_ANSWER,
            expected_keywords=SAMPLE_SCENARIO["expected_keywords"],
            model="gpt-4o-mini",
            rubric=None,
        )
        assert result["score"] == pytest.approx(0.88)

    @patch("apps.backend.app.judge_factory.openai_client")
    def test_openai_score_clamped_below_zero(self, mock_openai):
        from apps.backend.app.judge_factory import openai_judge

        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"score": -0.5, "reason": "Terrible."}'
        mock_openai.chat.completions.create.return_value = mock_response

        result = openai_judge(
            question="Q",
            context_docs=["C"],
            answer="A",
            expected_keywords=[],
            model="gpt-4o-mini",
            rubric=None,
        )
        assert result["score"] >= 0.0

    @patch("apps.backend.app.judge_factory.openai_client")
    def test_openai_handles_empty_response(self, mock_openai):
        from apps.backend.app.judge_factory import openai_judge

        mock_response = MagicMock()
        mock_response.choices[0].message.content = ""
        mock_openai.chat.completions.create.return_value = mock_response

        result = openai_judge(
            question="Q",
            context_docs=["C"],
            answer="A",
            expected_keywords=[],
            model="gpt-4o-mini",
            rubric=None,
        )
        assert 0.0 <= result["score"] <= 1.0


# ---------------------------------------------------------------------------
# Factory router
# ---------------------------------------------------------------------------

class TestJudgeFactoryRouter:
    """Verify the factory returns the right judge for each model name."""

    def test_groq_model_routes_to_groq_judge(self):
        from apps.backend.app.judge_factory import get_judge
        judge = get_judge("llama-3.1-8b-instant")
        assert callable(judge)
        # Function name should hint at the strategy
        assert "groq" in judge.__name__.lower() or "llm" in judge.__name__.lower()

    def test_openai_model_routes_to_openai_judge(self):
        from apps.backend.app.judge_factory import get_judge
        judge = get_judge("gpt-4o-mini")
        assert callable(judge)
        assert "openai" in judge.__name__.lower() or "llm" in judge.__name__.lower()

    def test_keyword_fallback_for_unknown_model(self):
        from apps.backend.app.judge_factory import get_judge
        judge = get_judge("unknown-model-xyz")
        assert callable(judge)

    def test_semantic_model_routes_correctly(self):
        from apps.backend.app.judge_factory import get_judge
        judge = get_judge("semantic")
        assert callable(judge)

"""
Judge factory for LLM Test Lab.

Usage:
    from llm_test_lab_core.judge_factory import get_judge

    judge = get_judge("llama-3.1-8b-instant")   # Groq
    judge = get_judge("claude-3-5-haiku")        # Claude (Anthropic)
    judge = get_judge("ollama:llama3")           # Ollama (local)

The factory reads API keys from environment variables automatically.
No key = graceful degradation (score=0.5, reason explains missing key).

Supported model strings
-----------------------
Groq (default):
  llama-3.1-8b-instant
  llama-3.3-70b-versatile
  mixtral-8x7b-32768
  gemma2-9b-it
  (any string not matching claude:* or ollama:*)

Claude (Anthropic):
  claude-3-5-haiku              -> claude-3-5-haiku-20241022
  claude-3-5-sonnet             -> claude-3-5-sonnet-20241022
  claude-3-haiku                -> claude-3-haiku-20240307
  claude-3-opus                 -> claude-3-opus-20240229
  claude:<any-full-model-id>    -> passed through verbatim

Ollama (local):
  ollama:<model>                -> e.g. ollama:llama3, ollama:mistral
"""

from __future__ import annotations

from typing import Union

# ---------------------------------------------------------------------------
# Claude model ID aliases (short name → full Anthropic model ID)
# ---------------------------------------------------------------------------
_CLAUDE_ALIASES: dict[str, str] = {
    "claude-3-5-haiku":   "claude-3-5-haiku-20241022",
    "claude-3-5-sonnet":  "claude-3-5-sonnet-20241022",
    "claude-3-haiku":     "claude-3-haiku-20240307",
    "claude-3-opus":      "claude-3-opus-20240229",
    "claude-3-sonnet":    "claude-3-sonnet-20240229",
}


def get_judge(model: str):
    """
    Return the correct JudgeClient for the given model string.

    Args:
        model: Model identifier string. See module docstring for full list.

    Returns:
        A JudgeClient instance (GroqJudgeClient, ClaudeJudgeClient, or OllamaJudgeClient).

    Raises:
        ValueError: If the model string format is invalid.
    """
    if not model or not isinstance(model, str):
        raise ValueError(f"model must be a non-empty string, got: {model!r}")

    model = model.strip()

    # --- Claude ---
    if model.startswith("claude:"):
        # explicit prefix: claude:<full-model-id>
        model_id = model[len("claude:"):]
        return _make_claude(model_id)

    if model in _CLAUDE_ALIASES or model.startswith("claude-"):
        # short alias or full claude-* string
        model_id = _CLAUDE_ALIASES.get(model, model)
        return _make_claude(model_id)

    # --- Ollama ---
    if model.startswith("ollama:"):
        ollama_model = model[len("ollama:"):]
        return _make_ollama(ollama_model)

    # --- Groq (default) ---
    return _make_groq(model)


# ---------------------------------------------------------------------------
# Internal constructors with lazy imports (keeps startup fast)
# ---------------------------------------------------------------------------

def _make_groq(model: str):
    from llm_test_lab_core.judges_groq import GroqJudgeClient
    return GroqJudgeClient(model=model)


def _make_claude(model_id: str):
    from llm_test_lab_core.judges_claude import ClaudeJudgeClient
    return ClaudeJudgeClient(model=model_id)


def _make_ollama(model: str):
    from llm_test_lab_core.judges_ollama import OllamaJudgeClient
    return OllamaJudgeClient(model=model)


# ---------------------------------------------------------------------------
# Supported model registry (used by dashboard + API for model picker UI)
# ---------------------------------------------------------------------------

SUPPORTED_MODELS = [
    # Groq
    {"id": "llama-3.1-8b-instant",      "provider": "groq",   "tier": "fast",     "label": "Llama 3.1 8B (Groq)"},
    {"id": "llama-3.3-70b-versatile",   "provider": "groq",   "tier": "accurate", "label": "Llama 3.3 70B (Groq)"},
    {"id": "mixtral-8x7b-32768",        "provider": "groq",   "tier": "fast",     "label": "Mixtral 8x7B (Groq)"},
    {"id": "gemma2-9b-it",              "provider": "groq",   "tier": "fast",     "label": "Gemma 2 9B (Groq)"},
    # Claude
    {"id": "claude-3-5-haiku",          "provider": "claude", "tier": "fast",     "label": "Claude 3.5 Haiku"},
    {"id": "claude-3-5-sonnet",         "provider": "claude", "tier": "accurate", "label": "Claude 3.5 Sonnet"},
    {"id": "claude-3-haiku",            "provider": "claude", "tier": "fast",     "label": "Claude 3 Haiku"},
    # Ollama (local)
    {"id": "ollama:llama3",             "provider": "ollama", "tier": "local",    "label": "Llama 3 (Ollama)"},
    {"id": "ollama:mistral",            "provider": "ollama", "tier": "local",    "label": "Mistral (Ollama)"},
    {"id": "ollama:gemma2",             "provider": "ollama", "tier": "local",    "label": "Gemma 2 (Ollama)"},
]

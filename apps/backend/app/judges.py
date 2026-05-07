"""Judge clients for Groq and Anthropic. Claude models are Pro-only.

Accuracy improvements (v2):
- G-Eval style: system prompt separates role from task
- Chain-of-thought reasoning before score (reduces position/verbosity bias)
- Ensemble scoring: 3 independent samples averaged (temperature spread)
- Structured scoring prompt: explicit criteria decomposition
- Score normalised to [0, 1] with clamp
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class JudgeResult:
    score: float
    reason: str


ANTHROPIC_MODELS: frozenset[str] = frozenset({
    "claude-3-haiku-20240307",
    "claude-3-sonnet-20240229",
    "claude-3-opus-20240229",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
})

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM_PROMPT = """\
You are an objective evaluator of AI-generated answers.
Your sole job is to score answers according to the rubric provided.
Do NOT favour longer answers — brevity and precision are virtues.
Do NOT favour responses that sound confident — ground every score in evidence.
Think step-by-step before assigning a score.
"""

_JUDGE_USER_TEMPLATE = """\
## Question
{question}

## Context (source of truth)
{context}

## Answer to evaluate
{answer}

## Rubric
{rubric}

## Scoring instructions
1. Identify the key claims in the answer.
2. Check each claim against the context.
3. Apply the rubric criteria one by one.
4. Assign a score in [0.0, 1.0] where:
   - 0.9-1.0 = fully correct, complete, well-grounded
   - 0.6-0.8 = mostly correct with minor gaps
   - 0.3-0.5 = partially correct or off-topic
   - 0.0-0.2 = incorrect, hallucinated, or irrelevant

Respond ONLY with valid JSON (no markdown, no preamble):
{{"score": <float 0-1>, "reason": "<one concise sentence citing the key evidence>"}}
"""

# Number of independent judge calls to average (ensemble).
# Higher = more accurate, higher cost. 3 is a good default.
_ENSEMBLE_N = int(os.environ.get("JUDGE_ENSEMBLE_N", "3"))
_ENSEMBLE_TEMPS = [0.0, 0.3, 0.6]  # Spread prevents mode collapse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_judge_json(raw: str) -> JudgeResult:
    """Robustly extract score + reason from LLM JSON response."""
    cleaned = (
        raw.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )
    try:
        data = json.loads(cleaned)
        return JudgeResult(
            score=max(0.0, min(1.0, float(data["score"]))),
            reason=str(data.get("reason", "")),
        )
    except (json.JSONDecodeError, KeyError, ValueError):
        # Fallback: scan for first float in [0,1]
        nums = re.findall(r"\b(0(?:\.\d+)?|1(?:\.0+)?)\b", cleaned)
        score = float(nums[0]) if nums else 0.5
        return JudgeResult(score=score, reason=cleaned[:200])


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BaseJudge:
    async def complete(self, *, question: str, context: str) -> str:
        raise NotImplementedError

    async def _single_judge(
        self,
        *,
        question: str,
        context: str,
        answer: str,
        rubric: str,
        temperature: float,
    ) -> JudgeResult:
        raise NotImplementedError

    async def judge(
        self,
        *,
        question: str,
        context: str,
        answer: str,
        rubric: str,
    ) -> JudgeResult:
        """Ensemble: average N independent scoring calls to reduce variance."""
        tasks = [
            self._single_judge(
                question=question,
                context=context,
                answer=answer,
                rubric=rubric or "Accuracy, relevance, completeness, groundedness.",
                temperature=t,
            )
            for t in _ENSEMBLE_TEMPS[:_ENSEMBLE_N]
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid = [r for r in results if isinstance(r, JudgeResult)]
        if not valid:
            logger.warning("All judge ensemble calls failed; returning 0.5")
            return JudgeResult(score=0.5, reason="Judge unavailable")
        avg_score = sum(r.score for r in valid) / len(valid)
        # Use the reason from the run closest to the average
        best = min(valid, key=lambda r: abs(r.score - avg_score))
        return JudgeResult(score=round(avg_score, 4), reason=best.reason)


# ---------------------------------------------------------------------------
# Groq
# ---------------------------------------------------------------------------

class GroqJudgeClient(BaseJudge):
    """Groq-hosted open models (Llama, Mixtral, Gemma)."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.api_key = os.environ["GROQ_API_KEY"]

    async def _chat(
        self, messages: list[dict], temperature: float = 0.0
    ) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 512,
                },
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

    async def complete(self, *, question: str, context: str) -> str:
        return await self._chat([
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"},
        ])

    async def _single_judge(
        self,
        *,
        question: str,
        context: str,
        answer: str,
        rubric: str,
        temperature: float,
    ) -> JudgeResult:
        user_msg = _JUDGE_USER_TEMPLATE.format(
            question=question,
            context=context or "(no context provided)",
            answer=answer,
            rubric=rubric,
        )
        raw = await self._chat(
            [
                {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=temperature,
        )
        return _parse_judge_json(raw)


# ---------------------------------------------------------------------------
# Anthropic
# ---------------------------------------------------------------------------

class AnthropicJudgeClient(BaseJudge):
    """Anthropic Claude models — Pro users only."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.api_key = os.environ["ANTHROPIC_API_KEY"]

    async def _chat(self, system: str, user: str, temperature: float = 0.0) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model_name,
                    "max_tokens": 512,
                    "system": system,
                    "messages": [{"role": "user", "content": user}],
                    "temperature": temperature,
                },
            )
            r.raise_for_status()
            return r.json()["content"][0]["text"]

    async def complete(self, *, question: str, context: str) -> str:
        return await self._chat(
            system="You are a helpful assistant.",
            user=f"Context: {context}\n\nQuestion: {question}",
        )

    async def _single_judge(
        self,
        *,
        question: str,
        context: str,
        answer: str,
        rubric: str,
        temperature: float,
    ) -> JudgeResult:
        user_msg = _JUDGE_USER_TEMPLATE.format(
            question=question,
            context=context or "(no context provided)",
            answer=answer,
            rubric=rubric,
        )
        raw = await self._chat(
            system=_JUDGE_SYSTEM_PROMPT,
            user=user_msg,
            temperature=temperature,
        )
        return _parse_judge_json(raw)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def judge_factory(model_name: str) -> BaseJudge:
    """Return the appropriate judge client.

    NOTE: Caller is responsible for enforcing the Pro gate before calling
    this factory for Anthropic models.
    """
    if model_name in ANTHROPIC_MODELS:
        return AnthropicJudgeClient(model_name)
    return GroqJudgeClient(model_name)

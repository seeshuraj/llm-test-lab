"""Judge clients for Groq and Anthropic. Claude models are Pro-only."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

import httpx


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


class BaseJudge:
    """Abstract base for all judge clients."""

    async def complete(self, *, question: str, context: str) -> str:
        raise NotImplementedError

    async def judge(
        self,
        *,
        question: str,
        context: str,
        answer: str,
        rubric: str,
    ) -> JudgeResult:
        raise NotImplementedError


class GroqJudgeClient(BaseJudge):
    """Groq-hosted open models (Llama, Mixtral, Gemma)."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.api_key = os.environ["GROQ_API_KEY"]

    async def _chat(self, messages: list[dict]) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model_name, "messages": messages, "temperature": 0},
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

    async def complete(self, *, question: str, context: str) -> str:
        return await self._chat([
            {"role": "user", "content": f"Context: {context}\n\nQuestion: {question}"}
        ])

    async def judge(
        self,
        *,
        question: str,
        context: str,
        answer: str,
        rubric: str,
    ) -> JudgeResult:
        prompt = (
            f"Rate the following answer on a scale of 0.0 to 1.0.\n"
            f"Question: {question}\nContext: {context}\nAnswer: {answer}\n"
            f"Rubric: {rubric or 'Accuracy, relevance, completeness.'}\n"
            "Reply with ONLY valid JSON: {\"score\": 0.0, \"reason\": \"...\"}\n"
            "Do not include any text outside the JSON object."
        )
        raw = await self._chat([{"role": "user", "content": prompt}])
        # Strip markdown code fences if model wraps response
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(cleaned)
        return JudgeResult(score=float(data["score"]), reason=str(data["reason"]))


class AnthropicJudgeClient(BaseJudge):
    """Anthropic Claude models — Pro users only."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.api_key = os.environ["ANTHROPIC_API_KEY"]

    async def _chat(self, prompt: str) -> str:
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
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            r.raise_for_status()
            return r.json()["content"][0]["text"]

    async def complete(self, *, question: str, context: str) -> str:
        return await self._chat(f"Context: {context}\n\nQuestion: {question}")

    async def judge(
        self,
        *,
        question: str,
        context: str,
        answer: str,
        rubric: str,
    ) -> JudgeResult:
        prompt = (
            f"Rate the following answer on a scale of 0.0 to 1.0.\n"
            f"Question: {question}\nContext: {context}\nAnswer: {answer}\n"
            f"Rubric: {rubric or 'Accuracy, relevance, completeness.'}\n"
            "Reply with ONLY valid JSON: {\"score\": 0.0, \"reason\": \"...\"}\n"
            "Do not include any text outside the JSON object."
        )
        raw = await self._chat(prompt)
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(cleaned)
        return JudgeResult(score=float(data["score"]), reason=str(data["reason"]))


def judge_factory(model_name: str) -> BaseJudge:
    """Return the appropriate judge client for the given model.

    NOTE: Caller is responsible for enforcing the Pro gate before calling
    this factory for Anthropic models. The factory itself does not check
    user tier — that check lives in the /api/runs endpoint.
    """
    if model_name in ANTHROPIC_MODELS:
        return AnthropicJudgeClient(model_name)
    return GroqJudgeClient(model_name)

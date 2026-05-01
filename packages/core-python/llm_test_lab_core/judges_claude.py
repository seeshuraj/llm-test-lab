"""
Claude judge client for LLM Test Lab.
Uses the Anthropic Messages API (claude-3-5-haiku or claude-3-5-sonnet).

Requires: ANTHROPIC_API_KEY environment variable.
Install:  pip install anthropic
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List

# Default judge model — Haiku is fast and cheap; swap to sonnet for highest accuracy
DEFAULT_CLAUDE_JUDGE = "claude-3-5-haiku-20241022"


class ClaudeJudgeClient:
    """
    JudgeClient implementation backed by Anthropic Claude.

    Matches the JudgeClient protocol in judges_base.py:
        async def score(question, answer, context_docs, rubric) -> Dict
    """

    def __init__(self, model: str = DEFAULT_CLAUDE_JUDGE):
        self.model = model
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    async def score(
        self,
        question: str,
        answer: str,
        context_docs: List[str],
        rubric: str,
        expected_keywords: List[str] = [],
    ) -> Dict:
        if not self.api_key:
            return {
                "score": 0.5,
                "reason": "ANTHROPIC_API_KEY not set",
                "judge_model": f"claude:{self.model}",
                "raw": "",
            }

        try:
            import anthropic
        except ImportError:
            return {
                "score": 0.5,
                "reason": "anthropic package not installed. Run: pip install anthropic",
                "judge_model": f"claude:{self.model}",
                "raw": "",
            }

        system_prompt = (
            "You are a strict, impartial evaluation model. "
            "Given a question, context documents, and an answer, "
            "score the answer between 0.0 and 1.0 on correctness and grounding. "
            "1.0 = perfectly correct and grounded. 0.0 = completely wrong or hallucinated. "
            "You MUST respond with ONLY a valid JSON object. No extra text, no markdown, no code fences. "
            'Exact format: {"score": 0.85, "reason": "one sentence explanation"}'
        )

        context_text = "\n".join(context_docs) if context_docs else "(no context provided)"

        keyword_instruction = ""
        if expected_keywords:
            kw_list = ", ".join(f'"{k}"' for k in expected_keywords)
            keyword_instruction = (
                f"\n\nRequired keywords: {kw_list}. "
                "Deduct at least 0.3 if ANY of these keywords are missing from the answer."
            )

        user_prompt = (
            f"Question: {question}\n\n"
            f"Context:\n{context_text}\n\n"
            f"Answer: {answer}\n\n"
            f"Rubric: {rubric}"
            f"{keyword_instruction}\n\n"
            'Respond ONLY with JSON: {"score": <float 0-1>, "reason": "<one sentence>"}'
        )

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        message = await client.messages.create(
            model=self.model,
            max_tokens=256,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        text = message.content[0].text.strip()
        return _parse_response(text, self.model)

    # ------------------------------------------------------------------
    # Compatibility shim: rag_metrics.py calls judge.judge(...) on older
    # paths. This wraps it to the standard score() interface.
    # ------------------------------------------------------------------
    async def judge(
        self,
        question: str,
        context: str,
        answer: str,
        rubric: str,
        _raw_prompt_override: str = "",
    ) -> object:
        prompt = _raw_prompt_override or rubric
        result = await self.score(
            question=question,
            answer=answer,
            context_docs=[context] if context else [],
            rubric=prompt,
        )

        class _Result:
            score = result["score"]
            reason = result.get("reason", "")
            judge_model = result.get("judge_model", "")

        return _Result()


def _parse_response(text: str, model: str) -> Dict:
    """Parse Claude JSON response with multi-level fallbacks."""
    # Try 1: direct parse
    try:
        parsed = json.loads(text)
        return _build_result(parsed, model, text)
    except json.JSONDecodeError:
        pass

    # Try 2: regex extract score + reason
    score_match = re.search(r'"score"\s*:\s*([0-9.]+)', text)
    reason_match = re.search(r'"reason"\s*:\s*"([^"]*)"', text)
    if score_match:
        return {
            "score": min(max(float(score_match.group(1)), 0.0), 1.0),
            "reason": reason_match.group(1) if reason_match else "Could not parse reason",
            "judge_model": f"claude:{model}",
            "raw": text,
        }

    # Try 3: extract JSON block
    start = text.find("{")
    end = text.rfind("}") + 1
    if start != -1 and end > start:
        snippet = re.sub(r',\s*}', '}', text[start:end])
        try:
            parsed = json.loads(snippet)
            return _build_result(parsed, model, text)
        except json.JSONDecodeError:
            pass

    # Fallback
    return {
        "score": 0.5,
        "reason": f"Could not parse judge response: {text[:120]}",
        "judge_model": f"claude:{model}",
        "raw": text,
    }


def _build_result(parsed: dict, model: str, raw: str) -> Dict:
    return {
        "score": min(max(float(parsed.get("score", 0.5)), 0.0), 1.0),
        "reason": str(parsed.get("reason", "")),
        "judge_model": f"claude:{model}",
        "raw": raw,
    }

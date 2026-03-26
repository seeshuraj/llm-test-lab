import json
import os
import re
from typing import List, Dict
import httpx

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Always use the strongest available model as judge for consistent, unbiased scoring
JUDGE_MODEL = "llama-3.3-70b-versatile"


class GroqJudgeClient:
    def __init__(self, model: str = "llama-3.1-8b-instant"):
        # 'model' param kept for API compatibility but judge always uses JUDGE_MODEL
        self.tested_model = model
        self.model = JUDGE_MODEL
        self.api_key = os.environ.get("GROQ_API_KEY", "")

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
                "reason": "GROQ_API_KEY not set",
                "judge_model": f"groq:{self.model}",
                "raw": "",
            }

        system_prompt = (
            "You are a strict, impartial evaluation model. "
            "Given a question, context documents, and an answer, "
            "score the answer between 0.0 and 1.0 on correctness and grounding. "
            "1.0 = perfectly correct and grounded. 0.0 = completely wrong or hallucinated. "
            "You MUST respond with ONLY a valid JSON object. No extra text, no markdown. "
            'Exact format: {"score": 0.85, "reason": "one sentence explanation"}'
        )

        context_text = "\n".join(context_docs) if context_docs else "(no context provided)"

        keyword_instruction = ""
        if expected_keywords:
            kw_list = ", ".join(f'"{k}"' for k in expected_keywords)
            keyword_instruction = (
                f"\n\nRequired keywords: {kw_list}. "
                "Penalise heavily (deduct at least 0.3) if ANY of these keywords are missing from the answer."
            )

        user_prompt = (
            f"Question: {question}\n\n"
            f"Context:\n{context_text}\n\n"
            f"Answer: {answer}\n\n"
            f"Rubric: {rubric}"
            f"{keyword_instruction}\n\n"
            'Respond ONLY with JSON: {"score": <float 0-1>, "reason": "<one sentence>"}'
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                GROQ_API_URL,
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    # temperature=0 for deterministic, reproducible scores
                    "temperature": 0,
                    "seed": 42,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        text = data["choices"][0]["message"]["content"].strip()

        # Try 1: direct parse
        try:
            parsed = json.loads(text)
            return _build_result(parsed, self.model, text)
        except json.JSONDecodeError:
            pass

        # Try 2: regex fallback
        score_match = re.search(r'"score"\s*:\s*([0-9.]+)', text)
        reason_match = re.search(r'"reason"\s*:\s*"([^"]*)"', text)

        if score_match:
            score = float(score_match.group(1))
            reason = reason_match.group(1) if reason_match else "Could not parse reason"
            return {
                "score": min(max(score, 0.0), 1.0),
                "reason": reason,
                "judge_model": f"groq:{self.model}",
                "raw": text,
            }

        # Try 3: extract JSON block
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            snippet = text[start:end]
            snippet = snippet.replace("\u201c", '"').replace("\u201d", '"')
            snippet = re.sub(r',\s*}', '}', snippet)
            try:
                parsed = json.loads(snippet)
                return _build_result(parsed, self.model, text)
            except json.JSONDecodeError:
                pass

        # Fallback
        return {
            "score": 0.5,
            "reason": f"Could not parse judge response: {text[:100]}",
            "judge_model": f"groq:{self.model}",
            "raw": text,
        }


def _build_result(parsed: dict, model: str, raw: str) -> Dict:
    return {
        "score": min(max(float(parsed.get("score", 0.5)), 0.0), 1.0),
        "reason": str(parsed.get("reason", "")),
        "judge_model": f"groq:{model}",
        "raw": raw,
    }

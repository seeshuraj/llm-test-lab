import json
from typing import List, Dict
import httpx


class OllamaJudgeClient:
    def __init__(
        self,
        model: str = "llama3",
        base_url: str = "http://localhost:11434",
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")

    async def score(
        self,
        question: str,
        answer: str,
        context_docs: List[str],
        rubric: str,
    ) -> Dict:
        system_prompt = (
            "You are a strict evaluation model. "
            "Given a question, context documents, and an answer, "
            "score the answer between 0.0 and 1.0 on correctness and grounding. "
            "1.0 = perfectly correct and grounded. 0.0 = completely wrong or hallucinated. "
            "Respond ONLY with valid JSON: {\"score\": <float>, \"reason\": \"<explanation>\"}"
        )

        context_text = "\n".join(context_docs) if context_docs else "(no context provided)"

        user_prompt = f"""Question: {question}

Context:
{context_text}

Answer: {answer}

Rubric: {rubric}

Respond ONLY with JSON like: {{"score": 0.85, "reason": "short explanation"}}"""

        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        text = data["choices"][0]["message"]["content"].strip()

        # Parse JSON from model output
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # Extract JSON substring if model adds extra text
            start = text.find("{")
            end = text.rfind("}") + 1
            parsed = json.loads(text[start:end])

        return {
            "score": float(parsed.get("score", 0.0)),
            "reason": parsed.get("reason", ""),
            "judge_model": f"ollama:{self.model}",
            "raw": text,
        }

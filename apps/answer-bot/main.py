import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Answer Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

BASE_SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question clearly and concisely. "
    "If context is provided, use it as your sole source of truth. "
    "If the answer is not in the context, say you don't know."
)


class QuestionRequest(BaseModel):
    question: str
    context: Optional[str] = None  # scenario context_docs passed from the eval runner


@app.get("/")
@app.head("/")
def health():
    return {"status": "ok", "model": GROQ_MODEL}


@app.get("/answer")
def answer_health():
    """Health probe — Render checks this with GET."""
    return {"status": "ok", "model": GROQ_MODEL, "key_set": bool(GROQ_API_KEY)}


@app.post("/answer")
async def answer(body: QuestionRequest):
    if not GROQ_API_KEY:
        return {"answer": f"Echo (no API key): {body.question}"}

    # Inject context into system prompt if provided
    system_prompt = BASE_SYSTEM_PROMPT
    if body.context and body.context.strip():
        system_prompt += (
            "\n\nYou are given the following CONTEXT. Treat it as the sole source of truth. "
            "Do not introduce any facts outside of it.\n\n"
            f"CONTEXT:\n{body.context.strip()}"
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": body.question},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 512,
                },
            )
            # Raise on 4xx/5xx from Groq — but catch below so we never return
            # HTTP 500 to the evaluator. A degraded answer is better than a crash.
            resp.raise_for_status()
            data = resp.json()
            answer_text = data["choices"][0]["message"]["content"].strip()
            return {"answer": answer_text}

    except httpx.HTTPStatusError as e:
        # Groq returned 4xx/5xx (e.g. invalid key → 401, rate limit → 429)
        status_code = e.response.status_code
        print(f"[answer-bot] Groq API error HTTP {status_code}: {e.response.text[:200]}")
        # Return a safe fallback — the LLM judge will score it low but CI won’t crash
        return {
            "answer": (
                f"Service temporarily unavailable (Groq HTTP {status_code}). "
                f"Question was: {body.question}"
            )
        }

    except httpx.TimeoutException:
        print("[answer-bot] Groq API timed out after 30s")
        return {
            "answer": (
                f"Request timed out reaching the language model. "
                f"Question was: {body.question}"
            )
        }

    except Exception as e:
        # Catch-all: log and return degraded response. Never expose a 500.
        print(f"[answer-bot] Unexpected error: {e}")
        return {
            "answer": (
                f"An unexpected error occurred. "
                f"Question was: {body.question}"
            )
        }

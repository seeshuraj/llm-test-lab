import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

SYSTEM_PROMPT = (
    "You are a helpful assistant. Answer the user's question clearly and concisely "
    "using only the information provided. If you don't know, say so."
)


class QuestionRequest(BaseModel):
    question: str


@app.get("/")
@app.head("/")
def health():
    return {"status": "ok", "model": GROQ_MODEL}


@app.get("/answer")
def answer_health():
    """Health probe endpoint — Render checks this with GET."""
    return {"status": "ok", "model": GROQ_MODEL, "key_set": bool(GROQ_API_KEY)}


@app.post("/answer")
async def answer(body: QuestionRequest):
    if not GROQ_API_KEY:
        return {"answer": f"Echo (no API key): {body.question}"}

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
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": body.question},
                ],
                "temperature": 0.2,
                "max_tokens": 512,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    answer_text = data["choices"][0]["message"]["content"].strip()
    return {"answer": answer_text}

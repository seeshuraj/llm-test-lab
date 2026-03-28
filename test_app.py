from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import os
import httpx
import uvicorn

app = FastAPI()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"


class QuestionRequest(BaseModel):
    question: str
    context: Optional[str] = None


@app.get("/answer")
def health():
    return {"status": "ok", "model": MODEL, "key_set": bool(GROQ_API_KEY)}


@app.post("/ask")
async def ask(body: QuestionRequest):
    if not GROQ_API_KEY:
        return {"answer": "GROQ_API_KEY not set on this server."}

    context_block = f"\n\nContext:\n{body.context}" if body.context else ""
    user_prompt = f"Question: {body.question}{context_block}\n\nAnswer concisely based on the context provided."

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": user_prompt}],
                "temperature": 0.2,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    answer = data["choices"][0]["message"]["content"].strip()
    return {"answer": answer}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))

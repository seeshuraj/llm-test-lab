from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

app = FastAPI()

class QuestionRequest(BaseModel):
    question: str

ANSWERS = {
    "What is LLM Test Lab?": "LLM Test Lab is a platform for evaluating RAG and AI agent systems using automated scoring.",
    "Who should use LLM Test Lab?": "AI engineers and developers who build and maintain LLM-powered applications should use LLM Test Lab.",
}

@app.post("/ask")
async def ask(body: QuestionRequest):
    answer = ANSWERS.get(body.question, "I don't know the answer to that question.")
    return {"answer": answer}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5001)

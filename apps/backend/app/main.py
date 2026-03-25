from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional
import uuid

import httpx as _httpx
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .db import engine, Base, get_db
from . import models
from llm_test_lab_core.models import Variant
from llm_test_lab_core.judges_groq import GroqJudgeClient
from llm_test_lab.scenarios_yaml import load_scenarios_from_yaml
from llm_test_lab.runner_local import run_suite
from .auth import hash_password, verify_password, create_access_token, get_current_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="LLM Test Lab Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth schemas ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(models.User).where(models.User.email == body.email))
    if res.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = models.User(
        id=str(uuid.uuid4()),
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    return TokenResponse(access_token=create_access_token(user.id))


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(models.User).where(models.User.email == form.username))
    user = res.scalars().first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenResponse(access_token=create_access_token(user.id))


@app.get("/api/auth/me", response_model=UserOut)
async def me(current_user: models.User = Depends(get_current_user)):
    return UserOut(id=current_user.id, email=current_user.email)


# ── Run schemas ───────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    scenarios_path: str
    project: str = "demo-project"
    variant_name: str = "demo-variant"
    app_url: Optional[str] = None
    app_bearer_token: Optional[str] = None


class ScenarioResultOut(BaseModel):
    scenario_id: str
    variant_id: str
    score: float
    reason: str
    latency_ms: float
    judge_model: str


class RunResponse(BaseModel):
    run_id: str
    project: str
    variant_name: str
    model_name: str
    created_at: Optional[str] = None
    results: List[ScenarioResultOut]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _map_run(run: models.Run) -> RunResponse:
    return RunResponse(
        run_id=run.id,
        project=run.project,
        variant_name=run.variant_name,
        model_name=run.model_name,
        created_at=run.created_at.isoformat() if run.created_at else None,
        results=[
            ScenarioResultOut(
                scenario_id=r.scenario_id,
                variant_id=r.variant_id,
                score=r.score,
                reason=r.reason,
                latency_ms=r.latency_ms,
                judge_model=r.judge_model,
            )
            for r in run.results
        ],
    )


# ── Run routes ────────────────────────────────────────────────────────────────

@app.post("/api/run-local", response_model=RunResponse)
async def run_local_eval(
    body: RunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    scenarios = load_scenarios_from_yaml(body.scenarios_path)

    variant = Variant(
        id=str(uuid.uuid4()),
        name=body.variant_name,
        model_name=body.app_url or "echo-model",
        rag_config={},
    )

    judge = GroqJudgeClient(model="llama3-8b-8192")
    run_id = str(uuid.uuid4())

    if body.app_url:
        headers = {}
        if body.app_bearer_token:
            headers["Authorization"] = f"Bearer {body.app_bearer_token}"
        app_url = body.app_url

        async def app_call(question: str) -> str:
            async with _httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    app_url,
                    json={"question": question},
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                return (
                    data.get("answer")
                    or data.get("response")
                    or data.get("output")
                    or data.get("text")
                    or str(data)
                )
    else:
        async def app_call(question: str) -> str:
            return f"Echo: {question}"

    run_result = await run_suite(
        run_id=run_id,
        project=body.project,
        variant=variant,
        scenarios=scenarios,
        judge=judge,
        app_call=app_call,
        rubric="Score answer from 0 to 1 on correctness and grounding.",
    )

    db_run = models.Run(
        id=run_result.run_id,
        project=run_result.project,
        variant_name=variant.name,
        model_name=variant.model_name,
        created_at=datetime.now(timezone.utc),
        user_id=current_user.id,
    )
    db.add(db_run)

    for r in run_result.results:
        db.add(models.RunScenarioResult(
            run_id=run_result.run_id,
            scenario_id=r.scenario_id,
            variant_id=r.variant_id,
            score=r.score,
            reason=r.reason,
            latency_ms=r.latency_ms,
            judge_model=r.judge_model,
        ))

    await db.commit()

    res = await db.execute(select(models.Run).where(models.Run.id == run_id))
    db_run = res.scalars().first()
    return _map_run(db_run)


@app.get("/api/runs", response_model=List[RunResponse])
async def list_runs(
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    res = await db.execute(
        select(models.Run)
        .where(models.Run.user_id == current_user.id)
        .order_by(models.Run.created_at.desc())
    )
    runs = res.scalars().unique().all()
    return [_map_run(run) for run in runs]


@app.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    res = await db.execute(
        select(models.Run).where(
            models.Run.id == run_id,
            models.Run.user_id == current_user.id,
        )
    )
    run = res.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _map_run(run)


@app.delete("/api/runs/{run_id}")
async def delete_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    res = await db.execute(
        select(models.Run).where(
            models.Run.id == run_id,
            models.Run.user_id == current_user.id,
        )
    )
    run = res.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    await db.delete(run)
    await db.commit()
    return {"deleted": run_id}

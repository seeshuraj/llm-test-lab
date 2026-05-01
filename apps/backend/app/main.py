"""LLM Test Lab — FastAPI backend (main entry point)."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
import yaml
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .api_keys import router as api_keys_router
from .auth import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
    verify_api_key,
)
from .datasets import router as datasets_router
from .db import get_db, init_db
from .models import ApiKey, Run, RunScenarioResult, ScenarioDataset, User
from .notifications import send_threshold_alert
from .rag_metrics import compute_rag_metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Ensure is_public column exists for existing deployments (safe no-op if already present)
    async for db in get_db():
        try:
            await db.execute(text(
                "ALTER TABLE runs ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            await db.commit()
        except Exception as exc:
            logger.warning("Migration skip (is_public): %s", exc)
        break
    yield


app = FastAPI(
    title="LLM Test Lab API",
    version="0.5.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
raw_origins = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173",
)
origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(api_keys_router, prefix="/api-keys")
app.include_router(datasets_router, prefix="/datasets")

# ---------------------------------------------------------------------------
# Free-trial gate
# ---------------------------------------------------------------------------
FREE_TRIAL_RUN_LIMIT = int(os.environ.get("FREE_TRIAL_RUN_LIMIT", "5"))


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class ModelDetailOut(BaseModel):
    id: str
    name: str
    provider: str
    description: str


class RunRequest(BaseModel):
    project: str
    variant_name: str
    model_name: str
    run_label: Optional[str] = None
    scenarios_yaml: Optional[str] = None
    rubric: Optional[str] = None
    app_endpoint_url: Optional[str] = None
    dataset_version_id: Optional[str] = None


class ScenarioResultOut(BaseModel):
    scenario_id: str
    variant_id: str
    score: float
    reason: str
    latency_ms: float
    judge_model: str
    faithfulness: Optional[float] = None
    answer_relevancy: Optional[float] = None
    context_precision: Optional[float] = None
    context_recall: Optional[float] = None


class RunOut(BaseModel):
    id: str
    project: str
    variant_name: str
    model_name: str
    run_label: Optional[str] = None
    created_at: Optional[datetime]
    mean_score: float
    results: list[ScenarioResultOut]
    dataset_version_id: Optional[str] = None
    is_public: bool = False


class RunSummaryOut(BaseModel):
    id: str
    project: str
    variant_name: str
    model_name: str
    run_label: Optional[str] = None
    created_at: Optional[datetime]
    mean_score: float
    dataset_version_id: Optional[str] = None
    is_public: bool = False


# Schema for the public share endpoint — matches the frontend Run type exactly
class ShareScenarioResultOut(BaseModel):
    scenario_id: str
    score: float
    latency_ms: float
    reason: str
    judge_model: str
    faithfulness: Optional[float] = None
    context_precision: Optional[float] = None
    answer_relevance: Optional[float] = None


class ShareRunOut(BaseModel):
    run_id: str
    project: str
    variant_name: str
    model_name: str
    created_at: Optional[datetime]
    avg_score: float
    results: list[ShareScenarioResultOut]


class ShareToggleRequest(BaseModel):
    is_public: bool


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.post("/auth/register", status_code=201)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        id=str(uuid.uuid4()),
        email=body.email,
        hashed_password=get_password_hash(body.password),
    )
    db.add(user)
    await db.commit()
    token = create_access_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/login")
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me")
async def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}


# ---------------------------------------------------------------------------
# Models catalogue
# ---------------------------------------------------------------------------

_MODELS: list[ModelDetailOut] = [
    ModelDetailOut(id="llama3-8b-8192", name="Llama 3 8B", provider="Groq", description="Fast, capable open model via Groq"),
    ModelDetailOut(id="llama3-70b-8192", name="Llama 3 70B", provider="Groq", description="Larger Llama 3 via Groq"),
    ModelDetailOut(id="mixtral-8x7b-32768", name="Mixtral 8x7B", provider="Groq", description="MoE model via Groq"),
    ModelDetailOut(id="gemma-7b-it", name="Gemma 7B", provider="Groq", description="Google Gemma 7B via Groq"),
    ModelDetailOut(id="claude-3-haiku-20240307", name="Claude 3 Haiku", provider="Anthropic", description="Fastest Claude model"),
    ModelDetailOut(id="claude-3-sonnet-20240229", name="Claude 3 Sonnet", provider="Anthropic", description="Balanced Claude model"),
    ModelDetailOut(id="claude-3-opus-20240229", name="Claude 3 Opus", provider="Anthropic", description="Most capable Claude model"),
]


@app.get("/models", response_model=list[ModelDetailOut])
async def list_models():
    return _MODELS


# ---------------------------------------------------------------------------
# Run execution
# ---------------------------------------------------------------------------

from .judges import judge_factory  # noqa: E402  (avoid circular at top)


async def _get_llm_answer(
    *,
    question: str,
    context: str,
    model_name: str,
    app_endpoint_url: Optional[str],
) -> tuple[str, float]:
    """Call the LLM (or app endpoint) and return (answer, latency_ms)."""
    t0 = time.monotonic()
    if app_endpoint_url:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                app_endpoint_url,
                json={"question": question, "context": context},
            )
            resp.raise_for_status()
            data = resp.json()
            answer = data.get("answer") or data.get("response") or str(data)
    else:
        judge = judge_factory(model_name)
        answer = await judge.complete(question=question, context=context)
    latency_ms = (time.monotonic() - t0) * 1000
    return answer, latency_ms


def _build_share_result(r: RunScenarioResult) -> ShareScenarioResultOut:
    rag = r.rag_scores or {}
    return ShareScenarioResultOut(
        scenario_id=r.scenario_id,
        score=r.score,
        latency_ms=r.latency_ms,
        reason=r.reason,
        judge_model=r.judge_model,
        faithfulness=rag.get("faithfulness"),
        context_precision=rag.get("context_precision"),
        answer_relevance=rag.get("answer_relevancy"),
    )


@app.post("/api/runs", response_model=RunOut, status_code=201)
async def create_run(
    body: RunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Free-trial gate
    run_count_result = await db.execute(
        select(func.count(Run.id)).where(Run.user_id == current_user.id)
    )
    run_count = run_count_result.scalar_one()
    if run_count >= FREE_TRIAL_RUN_LIMIT:
        raise HTTPException(
            status_code=402,
            detail=f"Free trial limit of {FREE_TRIAL_RUN_LIMIT} runs reached. Upgrade to Pro.",
        )

    scenarios_yaml = body.scenarios_yaml
    dataset_version_id = body.dataset_version_id

    if dataset_version_id and not scenarios_yaml:
        ds = await db.get(ScenarioDataset, dataset_version_id)
        if not ds:
            raise HTTPException(status_code=404, detail="Dataset version not found")
        scenarios_yaml = ds.yaml_content

    if not scenarios_yaml:
        raise HTTPException(status_code=400, detail="scenarios_yaml or dataset_version_id is required")

    try:
        scenarios_data = yaml.safe_load(scenarios_yaml)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {exc}")

    scenarios = scenarios_data.get("scenarios", [])
    if not scenarios:
        raise HTTPException(status_code=400, detail="No scenarios found in YAML")

    run_id = str(uuid.uuid4())
    judge = judge_factory(body.model_name)
    results: list[RunScenarioResult] = []

    for scenario in scenarios:
        scenario_id = scenario.get("id", str(uuid.uuid4()))
        question = scenario.get("question", "")
        context = scenario.get("context", "")
        variant_id = body.variant_name

        answer, latency_ms = await _get_llm_answer(
            question=question,
            context=context,
            model_name=body.model_name,
            app_endpoint_url=body.app_endpoint_url,
        )

        judge_result = await judge.judge(
            question=question,
            context=context,
            answer=answer,
            rubric=body.rubric or "",
        )

        rag_scores_dict: Optional[dict] = None
        if context:
            rag = await compute_rag_metrics(
                question=question,
                context=context,
                answer=answer,
                judge=judge,
            )
            rag_scores_dict = rag.to_dict()

        result = RunScenarioResult(
            run_id=run_id,
            scenario_id=scenario_id,
            variant_id=variant_id,
            score=judge_result.score,
            reason=judge_result.reason,
            latency_ms=latency_ms,
            judge_model=body.model_name,
            rag_scores=rag_scores_dict,
        )
        results.append(result)

    mean_score = sum(r.score for r in results) / len(results) if results else 0.0

    run = Run(
        id=run_id,
        project=body.project,
        variant_name=body.variant_name,
        model_name=body.model_name,
        run_label=body.run_label,
        created_at=datetime.now(timezone.utc),
        user_id=current_user.id,
        scenarios_yaml=scenarios_yaml,
        rubric=body.rubric,
        app_endpoint_url=body.app_endpoint_url,
        dataset_version_id=dataset_version_id,
        is_public=False,
    )
    db.add(run)
    for r in results:
        db.add(r)
    await db.commit()
    await db.refresh(run)

    threshold_env = os.environ.get("SCORE_FAIL_UNDER")
    if threshold_env:
        try:
            threshold = float(threshold_env)
            if mean_score < threshold:
                asyncio.create_task(
                    send_threshold_alert(
                        run_id=run_id,
                        project=body.project,
                        mean_score=mean_score,
                        threshold=threshold,
                    )
                )
        except ValueError:
            pass

    results_out = [
        ScenarioResultOut(
            scenario_id=r.scenario_id,
            variant_id=r.variant_id,
            score=r.score,
            reason=r.reason,
            latency_ms=r.latency_ms,
            judge_model=r.judge_model,
            **(r.rag_scores or {}),
        )
        for r in results
    ]

    return RunOut(
        id=run.id,
        project=run.project,
        variant_name=run.variant_name,
        model_name=run.model_name,
        run_label=run.run_label,
        created_at=run.created_at,
        mean_score=mean_score,
        results=results_out,
        dataset_version_id=dataset_version_id,
        is_public=False,
    )


# ---------------------------------------------------------------------------
# Run queries
# ---------------------------------------------------------------------------

@app.get("/api/runs", response_model=list[RunSummaryOut])
async def list_runs(
    project: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Run, func.avg(RunScenarioResult.score).label("mean_score"))
        .join(RunScenarioResult, Run.id == RunScenarioResult.run_id)
        .where(Run.user_id == current_user.id)
        .group_by(Run.id)
        .order_by(desc(Run.created_at))
    )
    if project:
        stmt = stmt.where(Run.project == project)

    rows = (await db.execute(stmt)).all()
    return [
        RunSummaryOut(
            id=row.Run.id,
            project=row.Run.project,
            variant_name=row.Run.variant_name,
            model_name=row.Run.model_name,
            run_label=row.Run.run_label,
            created_at=row.Run.created_at,
            mean_score=round(row.mean_score, 4),
            dataset_version_id=row.Run.dataset_version_id,
            is_public=row.Run.is_public,
        )
        for row in rows
    ]


@app.get("/api/runs/{run_id}", response_model=RunOut)
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Run)
        .options(selectinload(Run.results))
        .where(Run.id == run_id, Run.user_id == current_user.id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    mean_score = (
        sum(r.score for r in run.results) / len(run.results) if run.results else 0.0
    )
    results_out = [
        ScenarioResultOut(
            scenario_id=r.scenario_id,
            variant_id=r.variant_id,
            score=r.score,
            reason=r.reason,
            latency_ms=r.latency_ms,
            judge_model=r.judge_model,
            **(r.rag_scores or {}),
        )
        for r in run.results
    ]
    return RunOut(
        id=run.id,
        project=run.project,
        variant_name=run.variant_name,
        model_name=run.model_name,
        run_label=run.run_label,
        created_at=run.created_at,
        mean_score=mean_score,
        results=results_out,
        dataset_version_id=run.dataset_version_id,
        is_public=run.is_public,
    )


# ---------------------------------------------------------------------------
# Share routes
# ---------------------------------------------------------------------------

@app.get("/api/runs/{run_id}/share", response_model=ShareRunOut)
async def get_shared_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Public endpoint — no auth required.
    Returns the run only if is_public=True.
    """
    result = await db.execute(
        select(Run)
        .options(selectinload(Run.results))
        .where(Run.id == run_id, Run.is_public == True)  # noqa: E712
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found or not shared")

    avg_score = (
        sum(r.score for r in run.results) / len(run.results) if run.results else 0.0
    )
    return ShareRunOut(
        run_id=run.id,
        project=run.project,
        variant_name=run.variant_name,
        model_name=run.model_name,
        created_at=run.created_at,
        avg_score=round(avg_score, 4),
        results=[_build_share_result(r) for r in run.results],
    )


@app.patch("/api/runs/{run_id}/share", response_model=RunSummaryOut)
async def toggle_run_share(
    run_id: str,
    body: ShareToggleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Toggle public sharing for a run. Auth required — only the owner can share.
    PATCH /api/runs/{run_id}/share  { "is_public": true }
    """
    result = await db.execute(
        select(Run)
        .options(selectinload(Run.results))
        .where(Run.id == run_id, Run.user_id == current_user.id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    run.is_public = body.is_public
    await db.commit()
    await db.refresh(run)

    mean_score = (
        sum(r.score for r in run.results) / len(run.results) if run.results else 0.0
    )
    return RunSummaryOut(
        id=run.id,
        project=run.project,
        variant_name=run.variant_name,
        model_name=run.model_name,
        run_label=run.run_label,
        created_at=run.created_at,
        mean_score=round(mean_score, 4),
        dataset_version_id=run.dataset_version_id,
        is_public=run.is_public,
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}

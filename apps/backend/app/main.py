import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from .auth import router as auth_router, get_current_user
from .db import get_db, init_db
from .models import Run, RunScenarioResult, User

from llm_test_lab_core.models import Variant
from llm_test_lab_core.judges_groq import GroqJudgeClient
from llm_test_lab.scenarios_yaml import load_scenarios_from_string
from llm_test_lab.runner_local import run_suite

app = FastAPI(title="LLM Test Lab API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth")

DEFAULT_RUBRIC = (
    "Score the answer based on correctness, relevance to the question, "
    "and grounding in the provided context documents. "
    "Penalise hallucinations or answers that contradict the context."
)


@app.on_event("startup")
async def on_startup():
    await init_db()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RunLocalRequest(BaseModel):
    project: str
    variant_name: str = "v1"
    model_name: str = "llama-3.1-8b-instant"
    scenarios_yaml: str
    app_endpoint_url: Optional[str] = None


class ScenarioResultOut(BaseModel):
    scenario_id: str
    variant_id: str
    score: float
    reason: str
    latency_ms: float
    judge_model: str


class RunOut(BaseModel):
    run_id: str
    project: str
    variant_name: str
    model_name: str
    created_at: Optional[datetime]
    avg_score: float
    results: List[ScenarioResultOut]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_run_with_results(run_id: str, user_id: str, db: AsyncSession) -> RunOut:
    result = await db.execute(
        select(Run).where(Run.id == run_id, Run.user_id == user_id)
    )
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    res_result = await db.execute(
        select(RunScenarioResult).where(RunScenarioResult.run_id == run_id)
    )
    results = res_result.scalars().all()
    avg = sum(r.score for r in results) / len(results) if results else 0.0

    return RunOut(
        run_id=run.id,
        project=run.project,
        variant_name=run.variant_name,
        model_name=run.model_name,
        created_at=run.created_at,
        avg_score=round(avg, 4),
        results=[ScenarioResultOut(
            scenario_id=r.scenario_id,
            variant_id=r.variant_id,
            score=r.score,
            reason=r.reason,
            latency_ms=r.latency_ms,
            judge_model=r.judge_model,
        ) for r in results],
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/api/run-local", response_model=RunOut)
async def run_local(
    req: RunLocalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        scenarios = load_scenarios_from_string(req.scenarios_yaml)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid scenarios YAML: {e}")

    variant = Variant(
        id=req.variant_name,
        name=req.variant_name,
        model_name=req.model_name,
    )

    judge = GroqJudgeClient(model=req.model_name)

    if req.app_endpoint_url:
        async def app_call(question: str) -> str:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(req.app_endpoint_url, json={"question": question})
                resp.raise_for_status()
                return resp.json().get("answer", "")
    else:
        async def app_call(question: str) -> str:
            return f"Echo: {question}"

    run_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)

    run_result = await run_suite(
        run_id=run_id,
        project=req.project,
        variant=variant,
        scenarios=scenarios,
        judge=judge,
        app_call=app_call,
        rubric=DEFAULT_RUBRIC,
    )

    db_run = Run(
        id=run_id,
        project=req.project,
        variant_name=variant.name,
        model_name=variant.model_name,
        created_at=created_at,
        user_id=current_user.id,
    )
    db.add(db_run)

    for r in run_result.results:
        db.add(RunScenarioResult(
            run_id=run_id,
            scenario_id=r.scenario_id,
            variant_id=r.variant_id,
            score=r.score,
            reason=r.reason,
            latency_ms=r.latency_ms,
            judge_model=r.judge_model,
        ))

    await db.commit()

    avg = sum(r.score for r in run_result.results) / len(run_result.results) if run_result.results else 0.0

    return RunOut(
        run_id=run_id,
        project=req.project,
        variant_name=variant.name,
        model_name=variant.model_name,
        created_at=created_at,
        avg_score=round(avg, 4),
        results=[ScenarioResultOut(
            scenario_id=r.scenario_id,
            variant_id=r.variant_id,
            score=r.score,
            reason=r.reason,
            latency_ms=r.latency_ms,
            judge_model=r.judge_model,
        ) for r in run_result.results],
    )


@app.get("/api/runs", response_model=List[RunOut])
async def list_runs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Run)
        .where(Run.user_id == current_user.id)
        .order_by(Run.created_at.desc())
    )
    runs = result.scalars().all()

    out = []
    for run in runs:
        res_result = await db.execute(
            select(RunScenarioResult).where(RunScenarioResult.run_id == run.id)
        )
        results = res_result.scalars().all()
        avg = sum(r.score for r in results) / len(results) if results else 0.0
        out.append(RunOut(
            run_id=run.id,
            project=run.project,
            variant_name=run.variant_name,
            model_name=run.model_name,
            created_at=run.created_at,
            avg_score=round(avg, 4),
            results=[ScenarioResultOut(
                scenario_id=r.scenario_id,
                variant_id=r.variant_id,
                score=r.score,
                reason=r.reason,
                latency_ms=r.latency_ms,
                judge_model=r.judge_model,
            ) for r in results],
        ))
    return out


@app.get("/api/runs/{run_id}", response_model=RunOut)
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await _get_run_with_results(run_id, current_user.id, db)


@app.delete("/api/runs/{run_id}", status_code=204)
async def delete_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify ownership
    result = await db.execute(
        select(Run).where(Run.id == run_id, Run.user_id == current_user.id)
    )
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Delete child results first, then the run
    await db.execute(delete(RunScenarioResult).where(RunScenarioResult.run_id == run_id))
    await db.execute(delete(Run).where(Run.id == run_id))
    await db.commit()


@app.get("/health")
def health():
    return {"status": "ok"}

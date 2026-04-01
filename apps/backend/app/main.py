import os
import uuid
import time
from datetime import datetime, timezone
from typing import List, Optional
from collections import defaultdict

import httpx
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from .auth import router as auth_router, get_current_user
from .notifications import router as notifications_router
from .api_keys import router as api_keys_router
from .db import get_db, init_db
from .models import Run, RunScenarioResult, User
from .rag_metrics import compute_rag_metrics

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
app.include_router(api_keys_router, prefix="/api/keys")
app.include_router(notifications_router)

DEFAULT_RUBRIC = (
    "Score the answer based on correctness and grounding in the provided context. "
    "Rules: "
    "(1) If the context contains relevant information, the answer must use it accurately — score high for correct grounding, low for contradictions or hallucinations. "
    "(2) If the context does NOT contain relevant information for the question, a correct refusal such as "
    "'I don't know based on the provided context' or 'The context does not cover this' should score 0.85 or above. "
    "(3) If the context is irrelevant but the model answers correctly from general knowledge, score 0.3–0.5 — the answer may be factually right but it is not grounded. "
    "(4) Penalise any answer that contradicts the context, regardless of whether the contradiction is factually correct in the real world."
)

SUPPORTED_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
]

_user_last_run: dict[str, float] = defaultdict(float)
_user_running: set[str] = set()
RUN_COOLDOWN_SECONDS = 10


def _check_rate_limit(user_id: str):
    if user_id in _user_running:
        raise HTTPException(status_code=429, detail="You already have a run in progress. Please wait for it to finish.")
    since_last = time.monotonic() - _user_last_run[user_id]
    if since_last < RUN_COOLDOWN_SECONDS:
        wait = int(RUN_COOLDOWN_SECONDS - since_last) + 1
        raise HTTPException(status_code=429, detail=f"Please wait {wait}s before starting another run.")


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
    run_label: Optional[str] = None
    scenarios_yaml: str
    app_endpoint_url: Optional[str] = None
    rubric: Optional[str] = None
    enable_rag_metrics: bool = False


class RunLabelUpdate(BaseModel):
    run_label: str


class ScenarioResultOut(BaseModel):
    scenario_id: str
    variant_id: str
    score: float
    reason: str
    latency_ms: float
    judge_model: str
    rag_scores: Optional[dict] = None


class RunOut(BaseModel):
    run_id: str
    project: str
    variant_name: str
    model_name: str
    run_label: Optional[str] = None
    created_at: Optional[datetime]
    avg_score: float
    results: List[ScenarioResultOut]
    scenarios_yaml: Optional[str] = None
    rubric: Optional[str] = None
    app_endpoint_url: Optional[str] = None
    enable_rag_metrics: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _build_run_out(run: Run, results: list) -> RunOut:
    avg = sum(r.score for r in results) / len(results) if results else 0.0
    return RunOut(
        run_id=run.id,
        project=run.project,
        variant_name=run.variant_name,
        model_name=run.model_name,
        run_label=run.run_label,
        created_at=run.created_at,
        avg_score=round(avg, 4),
        scenarios_yaml=run.scenarios_yaml,
        rubric=run.rubric,
        app_endpoint_url=run.app_endpoint_url,
        results=[ScenarioResultOut(
            scenario_id=r.scenario_id,
            variant_id=r.variant_id,
            score=r.score,
            reason=r.reason,
            latency_ms=r.latency_ms,
            judge_model=r.judge_model,
            rag_scores=r.rag_scores,
        ) for r in results],
    )


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
    return await _build_run_out(run, results)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/models")
def list_models():
    return {"models": SUPPORTED_MODELS}


@app.post("/api/run-local", response_model=RunOut)
async def run_local(
    req: RunLocalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_rate_limit(current_user.id)

    if req.model_name not in SUPPORTED_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported model '{req.model_name}'. Supported: {SUPPORTED_MODELS}"
        )

    try:
        scenarios = load_scenarios_from_string(req.scenarios_yaml)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid scenarios YAML: {e}")

    rubric = req.rubric.strip() if req.rubric and req.rubric.strip() else DEFAULT_RUBRIC

    variant = Variant(
        id=req.variant_name,
        name=req.variant_name,
        model_name=req.model_name,
    )

    judge = GroqJudgeClient(model=req.model_name)

    if req.app_endpoint_url:
        async def app_call(question: str, context: str = "") -> str:
            payload = {"question": question}
            if context:
                payload["context"] = context
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(req.app_endpoint_url, json=payload)
                resp.raise_for_status()
                return resp.json().get("answer", "")
    else:
        async def app_call(question: str, context: str = "") -> str:
            return f"Echo: {question}"

    run_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)

    _user_running.add(current_user.id)
    try:
        run_result = await run_suite(
            run_id=run_id,
            project=req.project,
            variant=variant,
            scenarios=scenarios,
            judge=judge,
            app_call=app_call,
            rubric=rubric,
        )
    finally:
        _user_running.discard(current_user.id)
        _user_last_run[current_user.id] = time.monotonic()

    db_run = Run(
        id=run_id,
        project=req.project,
        variant_name=variant.name,
        model_name=variant.model_name,
        run_label=req.run_label.strip() if req.run_label and req.run_label.strip() else None,
        created_at=created_at,
        user_id=current_user.id,
        scenarios_yaml=req.scenarios_yaml,
        rubric=rubric,
        app_endpoint_url=req.app_endpoint_url,
    )
    db.add(db_run)

    for r in run_result.results:
        rag_scores_dict = None
        if req.enable_rag_metrics:
            matching_scenario = next(
                (s for s in scenarios if s.id == r.scenario_id), None
            )
            context_text = getattr(matching_scenario, "context", "") or ""
            question_text = getattr(matching_scenario, "question", "") or ""
            answer_text = getattr(r, "answer", "") or getattr(r, "reason", "")

            if context_text and question_text:
                try:
                    rag_scores = await compute_rag_metrics(
                        question=question_text,
                        context=context_text,
                        answer=answer_text,
                        judge=judge,
                    )
                    rag_scores_dict = rag_scores.to_dict()
                except Exception:
                    rag_scores_dict = None

        db.add(RunScenarioResult(
            run_id=run_id,
            scenario_id=r.scenario_id,
            variant_id=r.variant_id,
            score=r.score,
            reason=r.reason,
            latency_ms=r.latency_ms,
            judge_model=r.judge_model,
            rag_scores=rag_scores_dict,
        ))

    await db.commit()
    return await _build_run_out(db_run, run_result.results)


@app.patch("/api/runs/{run_id}/label", response_model=RunOut)
async def update_run_label(
    run_id: str,
    body: RunLabelUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Run).where(Run.id == run_id, Run.user_id == current_user.id)
    )
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run.run_label = body.run_label.strip() or None
    await db.commit()
    await db.refresh(run)
    return await _get_run_with_results(run_id, current_user.id, db)


@app.post("/api/runs/{run_id}/rerun", response_model=RunOut)
async def rerun(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Run).where(Run.id == run_id, Run.user_id == current_user.id)
    )
    original = result.scalars().first()
    if not original:
        raise HTTPException(status_code=404, detail="Run not found")
    if not original.scenarios_yaml:
        raise HTTPException(status_code=400, detail="Original run has no stored YAML — cannot re-run")

    model = original.model_name if original.model_name in SUPPORTED_MODELS else SUPPORTED_MODELS[0]

    req = RunLocalRequest(
        project=original.project,
        variant_name=original.variant_name,
        model_name=model,
        run_label=original.run_label,
        scenarios_yaml=original.scenarios_yaml,
        rubric=original.rubric,
        app_endpoint_url=original.app_endpoint_url,
    )
    return await run_local(req, db, current_user)


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
        out.append(await _build_run_out(run, results))
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
    result = await db.execute(
        select(Run).where(Run.id == run_id, Run.user_id == current_user.id)
    )
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    await db.execute(delete(RunScenarioResult).where(RunScenarioResult.run_id == run_id))
    await db.execute(delete(Run).where(Run.id == run_id))
    await db.commit()


# ---------------------------------------------------------------------------
# Public share route — NO auth required
# ---------------------------------------------------------------------------

@app.get("/api/share/{run_id}", response_model=RunOut)
async def get_shared_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Run).where(Run.id == run_id))
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    res_result = await db.execute(
        select(RunScenarioResult).where(RunScenarioResult.run_id == run_id)
    )
    results = res_result.scalars().all()
    return await _build_run_out(run, results)


@app.get("/health")
def health():
    return {"status": "ok"}

from contextlib import asynccontextmanager
from typing import List
import uuid

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .db import engine, Base, get_db
from . import models
from llm_test_lab_core.models import Variant
from llm_test_lab_core.judges_ollama import OllamaJudgeClient
from llm_test_lab.scenarios_yaml import load_scenarios_from_yaml
from llm_test_lab.runner_local import run_suite


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="LLM Test Lab Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    scenarios_path: str
    project: str = "demo-project"
    variant_name: str = "demo-variant"


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
    results: List[ScenarioResultOut]


def _map_run(run: models.Run) -> RunResponse:
    return RunResponse(
        run_id=run.id,
        project=run.project,
        variant_name=run.variant_name,
        model_name=run.model_name,
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


@app.post("/api/run-local", response_model=RunResponse)
async def run_local_eval(body: RunRequest, db: AsyncSession = Depends(get_db)):
    scenarios = load_scenarios_from_yaml(body.scenarios_path)

    variant = Variant(
        id=str(uuid.uuid4()),
        name=body.variant_name,
        model_name="dummy-app-model",
        rag_config={},
    )

    judge = OllamaJudgeClient(model="llama3")
    run_id = str(uuid.uuid4())

    run_result = await run_suite(
        run_id=run_id,
        project=body.project,
        variant=variant,
        scenarios=scenarios,
        judge=judge,
        app_call=lambda q: f"Echo: {q}",
        rubric="Score answer from 0 to 1 on correctness and grounding.",
    )

    db_run = models.Run(
        id=run_result.run_id,
        project=run_result.project,
        variant_name=variant.name,
        model_name=variant.model_name,
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
async def list_runs(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(models.Run).order_by(models.Run.created_at.desc()))
    runs = res.scalars().unique().all()
    return [_map_run(run) for run in runs]


@app.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(models.Run).where(models.Run.id == run_id))
    run = res.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _map_run(run)

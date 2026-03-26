from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class Scenario(BaseModel):
    id: str
    name: Optional[str] = None      # optional — defaults to id if not provided
    question: str
    context_docs: List[str] = []
    expected_answer: Optional[str] = None
    expected_keywords: List[str] = []  # used in YAML but not required
    tags: List[str] = []


class Variant(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: str
    name: str
    model_name: str
    rag_config: dict = {}


class ScenarioResult(BaseModel):
    scenario_id: str
    variant_id: str
    score: float
    reason: str
    latency_ms: float
    judge_model: str


class RunResult(BaseModel):
    run_id: str
    project: str
    variant: Variant
    results: List[ScenarioResult]

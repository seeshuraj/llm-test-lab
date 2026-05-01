from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class Scenario(BaseModel):
    id: str
    name: Optional[str] = None      # defaults to id if not provided
    question: str
    context_docs: List[str] = []
    expected_answer: Optional[str] = None
    expected_keywords: List[str] = []
    tags: List[str] = []


class Variant(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: str
    name: str
    model_name: str
    rag_config: dict = {}


class MetricScore(BaseModel):
    """A single named metric with score + explanation."""
    name: str
    score: float = Field(ge=0.0, le=1.0)
    reason: str = ""
    judge_model: str = ""


class ScenarioResult(BaseModel):
    scenario_id: str
    variant_id: str

    # --- Composite ---
    score: float = Field(ge=0.0, le=1.0, description="Mean of all metric scores")
    reason: str = ""
    latency_ms: float = 0.0
    judge_model: str = ""

    # --- Individual RAG metrics (None = metric was skipped) ---
    faithfulness: Optional[MetricScore] = None
    answer_relevancy: Optional[MetricScore] = None
    context_recall: Optional[MetricScore] = None
    context_precision: Optional[MetricScore] = None

    # --- Raw LLM answer captured during evaluation ---
    answer: str = ""

    @property
    def passed(self) -> bool:
        """Convenience: True if composite score >= 0.7."""
        return self.score >= 0.7


class RunResult(BaseModel):
    run_id: str
    project: str
    variant: Variant
    results: List[ScenarioResult]

    @property
    def mean_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.score for r in self.results) / len(self.results)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)

import time
from typing import List, Callable
from llm_test_lab_core.judges_ollama import OllamaJudgeClient
from llm_test_lab_core.models import Scenario, RunResult, ScenarioResult


async def run_suite(
    run_id: str,
    project: str,
    variant,
    scenarios: List[Scenario],
    judge: OllamaJudgeClient,
    app_call: Callable,
    rubric: str,
) -> RunResult:
    results: List[ScenarioResult] = []

    for scenario in scenarios:
        raw_answer = app_call(scenario.question)

        start = time.perf_counter()
        scored = await judge.score(
            question=scenario.question,
            answer=raw_answer,
            context_docs=scenario.context_docs,
            rubric=rubric,
        )
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        results.append(
            ScenarioResult(
                scenario_id=scenario.id,
                variant_id=variant.id,
                score=scored["score"],
                reason=scored.get("reason", ""),
                latency_ms=latency_ms,
                judge_model=scored.get("judge_model", ""),
            )
        )

    return RunResult(
        run_id=run_id,
        project=project,
        variant=variant,
        results=results,
    )

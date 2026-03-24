import time
from typing import List, Callable

from llm_test_lab_core.models import Scenario, Variant, RunResult, ScenarioResult


async def run_suite(
    run_id: str,
    project: str,
    variant: Variant,
    scenarios: List[Scenario],
    judge,
    app_call: Callable[[str], str],
    rubric: str,
) -> RunResult:
    results: List[ScenarioResult] = []

    for sc in scenarios:
        start = time.perf_counter()
        answer = app_call(sc.question)
        latency_ms = (time.perf_counter() - start) * 1000

        scored = await judge.score(
            question=sc.question,
            answer=answer,
            context_docs=sc.context_docs,
            rubric=rubric,
        )

        results.append(
            ScenarioResult(
                scenario_id=sc.id,
                variant_id=variant.id,
                score=float(scored["score"]),
                reason=scored.get("reason", ""),
                latency_ms=latency_ms,
                judge_model=scored.get("judge_model", "unknown"),
            )
        )

    return RunResult(
        run_id=run_id,
        project=project,
        variant=variant,
        results=results,
    )

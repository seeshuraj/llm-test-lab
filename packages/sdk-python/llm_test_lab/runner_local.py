import asyncio
import time
from typing import List, Callable
from llm_test_lab_core.models import Scenario, RunResult, ScenarioResult

# Max concurrent scenario evaluations — avoids overwhelming Groq rate limits
CONCURRENCY = 5


async def _run_scenario(
    scenario: Scenario,
    variant,
    judge,
    app_call: Callable,
    rubric: str,
    sem: asyncio.Semaphore,
) -> ScenarioResult:
    async with sem:
        context_text = "\n\n".join(scenario.context_docs) if scenario.context_docs else ""

        # Time ONLY the app response — not judge overhead
        start = time.perf_counter()
        try:
            if asyncio.iscoroutinefunction(app_call):
                raw_answer = await app_call(scenario.question, context_text)
            else:
                raw_answer = app_call(scenario.question, context_text)
            app_error = None
        except Exception as e:
            raw_answer = ""
            app_error = f"App endpoint error: {type(e).__name__}: {str(e)[:120]}"
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        if app_error:
            return ScenarioResult(
                scenario_id=scenario.id,
                variant_id=variant.id,
                score=0.0,
                reason=app_error,
                latency_ms=latency_ms,
                judge_model="none",
            )

        scored = await judge.score(
            question=scenario.question,
            answer=raw_answer,
            context_docs=scenario.context_docs,
            rubric=rubric,
            expected_keywords=scenario.expected_keywords,
        )

        return ScenarioResult(
            scenario_id=scenario.id,
            variant_id=variant.id,
            score=scored["score"],
            reason=scored.get("reason", ""),
            latency_ms=latency_ms,
            judge_model=scored.get("judge_model", ""),
        )


async def run_suite(
    run_id: str,
    project: str,
    variant,
    scenarios: List[Scenario],
    judge,
    app_call: Callable,
    rubric: str,
) -> RunResult:
    sem = asyncio.Semaphore(CONCURRENCY)
    tasks = [
        _run_scenario(scenario, variant, judge, app_call, rubric, sem)
        for scenario in scenarios
    ]
    results: List[ScenarioResult] = await asyncio.gather(*tasks)

    return RunResult(
        run_id=run_id,
        project=project,
        variant=variant,
        results=list(results),
    )

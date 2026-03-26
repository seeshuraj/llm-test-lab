import time
from typing import List, Callable, Awaitable, Union
from llm_test_lab_core.judges_ollama import OllamaJudgeClient
from llm_test_lab_core.models import Scenario, RunResult, ScenarioResult
import asyncio


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
        # Build flat context string from scenario context_docs
        context_text = "\n\n".join(scenario.context_docs) if scenario.context_docs else ""

        # Time only the app_call (network + LLM round-trip)
        start = time.perf_counter()
        if asyncio.iscoroutinefunction(app_call):
            raw_answer = await app_call(scenario.question, context_text)
        else:
            raw_answer = app_call(scenario.question, context_text)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        scored = await judge.score(
            question=scenario.question,
            answer=raw_answer,
            context_docs=scenario.context_docs,
            rubric=rubric,
        )

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

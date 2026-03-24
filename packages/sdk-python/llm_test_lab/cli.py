import asyncio
import argparse
import json
import sys
import uuid
from llm_test_lab_core.models import Variant
from llm_test_lab_core.judges_ollama import OllamaJudgeClient
from llm_test_lab.scenarios_yaml import load_scenarios_from_yaml
from llm_test_lab.runner_local import run_suite


def main():
    parser = argparse.ArgumentParser(
        prog="llm-test-lab",
        description="LLM Test Lab — CLI evaluation runner",
    )
    parser.add_argument("--scenarios", required=True, help="Path to scenarios.yaml")
    parser.add_argument("--project", default="cli-run", help="Project name")
    parser.add_argument("--variant", default="v1", help="Variant name")
    parser.add_argument("--model", default="llama3", help="Ollama model to use as judge")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama base URL")
    parser.add_argument("--fail-under", type=float, default=None, help="Fail if avg score below this (0.0–1.0)")
    parser.add_argument("--output", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--push", default=None, help="Backend URL to push results (e.g. http://localhost:8000)")

    args = parser.parse_args()

    asyncio.run(_run(args))


async def _run(args):
    print(f"[llm-test-lab] Loading scenarios from: {args.scenarios}")
    scenarios = load_scenarios_from_yaml(args.scenarios)
    print(f"[llm-test-lab] Found {len(scenarios)} scenario(s)")

    variant = Variant(
        id=str(uuid.uuid4()),
        name=args.variant,
        model_name="cli-app-model",
        rag_config={},
    )

    judge = OllamaJudgeClient(model=args.model, base_url=args.ollama_url)
    run_id = str(uuid.uuid4())

    print(f"[llm-test-lab] Running evaluation (judge: {args.model})...\n")

    run_result = await run_suite(
        run_id=run_id,
        project=args.project,
        variant=variant,
        scenarios=scenarios,
        judge=judge,
        app_call=lambda q: f"Echo: {q}",
        rubric="Score answer from 0 to 1 on correctness and grounding.",
    )

    # Calculate avg
    scores = [r.score for r in run_result.results]
    avg = sum(scores) / len(scores) if scores else 0.0

    if args.output == "json":
        output = {
            "run_id": run_result.run_id,
            "project": run_result.project,
            "variant": args.variant,
            "avg_score": round(avg, 4),
            "results": [
                {
                    "scenario_id": r.scenario_id,
                    "score": r.score,
                    "latency_ms": r.latency_ms,
                    "reason": r.reason,
                    "judge_model": r.judge_model,
                }
                for r in run_result.results
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"{'Scenario':<12} {'Score':>6} {'Latency':>12}  Reason")
        print("─" * 80)
        for r in run_result.results:
            print(f"{r.scenario_id:<12} {r.score:>6.2f} {r.latency_ms:>10.0f}ms  {r.reason[:60]}")
        print("─" * 80)
        print(f"{'AVG':<12} {avg:>6.2f}")

    # Push to backend if requested
    if args.push:
        import httpx
        url = f"{args.push.rstrip('/')}/api/run-local"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json={
                    "scenarios_path": args.scenarios,
                    "project": args.project,
                    "variant_name": args.variant,
                })
                if resp.status_code == 200:
                    print(f"\n[llm-test-lab] ✅ Results pushed to {url}")
                else:
                    print(f"\n[llm-test-lab] ⚠ Push failed: {resp.status_code}")
        except Exception as e:
            print(f"\n[llm-test-lab] ⚠ Push error: {e}")

    # CI gate
    if args.fail_under is not None:
        if avg < args.fail_under:
            print(f"\n[llm-test-lab] ❌ FAILED — avg score {avg:.4f} < threshold {args.fail_under}")
            sys.exit(1)
        else:
            print(f"\n[llm-test-lab] ✅ PASSED — avg score {avg:.4f} >= threshold {args.fail_under}")
            sys.exit(0)
if __name__ == "__main__":
    main()

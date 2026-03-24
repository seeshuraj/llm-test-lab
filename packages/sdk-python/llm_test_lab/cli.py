import argparse
import uuid
import asyncio

from llm_test_lab_core.judges_ollama import OllamaJudgeClient
from llm_test_lab_core.models import Variant
from llm_test_lab.scenarios_yaml import load_scenarios_from_yaml
from llm_test_lab.runner_local import run_suite


def demo_app_call(question: str) -> str:
    return f"Echo: {question}"


class DummyJudge:
    async def score(self, question, answer, context_docs, rubric):
        return {
            "score": 0.5,
            "reason": "Dummy judge, always 0.5",
            "judge_model": "dummy",
        }


def cmd_run(args):
    scenarios = load_scenarios_from_yaml(args.scenarios)

    variant = Variant(
        id=str(uuid.uuid4()),
        name=args.variant,
        model_name="dummy-model",
        rag_config={},
    )

    judge = OllamaJudgeClient(model="llama3")

    run_id = str(uuid.uuid4())

    async def _run():
        return await run_suite(
            run_id=run_id,
            project=args.project,
            variant=variant,
            scenarios=scenarios,
            judge=judge,
            app_call=demo_app_call,
            rubric="Score answer from 0 to 1 on correctness and grounding.",
        )

    result = asyncio.run(_run())

    print(f"\nRun ID : {run_id}")
    print(f"Scenarios: {len(result.results)}")
    for r in result.results:
        print(
            f"  [{r.scenario_id}] score={r.score:.2f}  "
            f"latency={r.latency_ms:.1f}ms  judge={r.judge_model}"
        )


def main():
    parser = argparse.ArgumentParser(prog="llm-test-lab", description="LLM Test Lab CLI")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run local evaluation")
    run_parser.add_argument("--scenarios", required=True, help="Path to scenarios YAML")
    run_parser.add_argument("--project", default="demo-project", help="Project name")
    run_parser.add_argument("--variant", default="demo-variant", help="Variant name")

    args = parser.parse_args()

    if args.command == "run":
        cmd_run(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

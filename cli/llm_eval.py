#!/usr/bin/env python3
"""
LLM Test Lab CLI
Usage:
  python cli/llm_eval.py \
    --api-url https://your-backend.railway.app \
    --token $LLM_TEST_LAB_TOKEN \
    --scenarios scenarios.yaml \
    --project my-app \
    --variant v1.2 \
    [--model llama-3.1-8b-instant] \
    [--app-url https://your-app.com/answer] \
    [--fail-under 0.7]
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error


def parse_args():
    p = argparse.ArgumentParser(description="LLM Test Lab — run evaluations from CI")
    p.add_argument("--api-url", required=True, help="Backend base URL")
    p.add_argument("--token", required=True, help="LLM Test Lab JWT token")
    p.add_argument("--scenarios", required=True, help="Path to scenarios YAML file")
    p.add_argument("--project", required=True, help="Project name")
    p.add_argument("--variant", required=True, help="Variant / version label")
    p.add_argument("--model", default="llama-3.1-8b-instant", help="Model to evaluate with")
    p.add_argument("--app-url", default=None, help="Your app endpoint URL (optional)")
    p.add_argument("--run-label", default=None, help="Human-readable label for this run")
    p.add_argument("--fail-under", type=float, default=None,
                   help="Exit code 1 if avg score is below this threshold (0.0-1.0)")
    return p.parse_args()


def read_file(path):
    with open(path, "r") as f:
        return f.read()


def post_json(url, payload, token):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"\n❌ HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"\n❌ Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def print_results(run):
    results = run.get("results", [])
    avg = run.get("avg_score", 0)
    run_id = run.get("run_id", "unknown")

    print(f"\n{'─'*60}")
    print(f"  LLM Test Lab — Evaluation Results")
    print(f"{'─'*60}")
    print(f"  Run ID   : {run_id}")
    print(f"  Project  : {run.get('project', '')}")
    print(f"  Variant  : {run.get('variant_name', '')}")
    print(f"  Model    : {run.get('model_name', '')}")
    print(f"  Scenarios: {len(results)}")
    print(f"{'─'*60}")

    passed = 0
    for r in results:
        score = r.get("score", 0)
        icon = "✅" if score >= 0.8 else "⚠️ " if score >= 0.5 else "❌"
        if score >= 0.8:
            passed += 1
        sid = r.get("scenario_id", "")[:30]
        rag = r.get("rag_metrics", {})
        rag_str = ""
        if rag:
            rag_str = (f"  [F:{rag.get('faithfulness',0):.2f}"
                       f" CR:{rag.get('context_recall',0):.2f}"
                       f" AR:{rag.get('answer_relevancy',0):.2f}"
                       f" CP:{rag.get('context_precision',0):.2f}]")
        print(f"  {icon} [{score:.2f}] {sid}{rag_str}")

    pass_rate = (passed / len(results) * 100) if results else 0
    avg_color = "" 
    print(f"{'─'*60}")
    print(f"  Avg Score : {avg:.3f}")
    print(f"  Pass Rate : {pass_rate:.0f}% ({passed}/{len(results)} passed ≥0.8)")
    print(f"{'─'*60}\n")
    return avg


def main():
    args = parse_args()

    print(f"\n🧪 LLM Test Lab CI")
    print(f"   Project : {args.project}")
    print(f"   Variant : {args.variant}")
    print(f"   Model   : {args.model}")
    print(f"   Scenarios: {args.scenarios}")
    if args.app_url:
        print(f"   App URL : {args.app_url}")
    print()

    scenarios_yaml = read_file(args.scenarios)

    payload = {
        "scenarios_yaml": scenarios_yaml,
        "project": args.project,
        "variant_name": args.variant,
        "model_name": args.model,
        "run_label": args.run_label or f"CI: {args.variant}",
        "app_endpoint_url": args.app_url,
    }

    print("⏳ Running evaluation...")
    start = time.time()
    run = post_json(f"{args.api_url.rstrip('/')}/api/run-local", payload, args.token)
    elapsed = time.time() - start
    print(f"✅ Completed in {elapsed:.1f}s")

    avg = print_results(run)

    if args.fail_under is not None:
        if avg < args.fail_under:
            print(f"❌ FAILED: avg score {avg:.3f} is below threshold {args.fail_under}")
            sys.exit(1)
        else:
            print(f"✅ PASSED: avg score {avg:.3f} >= threshold {args.fail_under}")

    sys.exit(0)


if __name__ == "__main__":
    main()

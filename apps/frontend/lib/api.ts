const API_BASE = "http://127.0.0.1:8000";

export interface ScenarioResult {
  scenario_id: string;
  variant_id: string;
  score: number;
  reason: string;
  latency_ms: number;
  judge_model: string;
}

export interface Run {
  run_id: string;
  project: string;
  variant_name: string;
  results: ScenarioResult[];
  created_at?: string;   // add this
}


export async function fetchRuns(): Promise<Run[]> {
  const res = await fetch(`${API_BASE}/api/runs`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch runs");
  return res.json();
}

export async function fetchRun(runId: string): Promise<Run> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Run not found");
  return res.json();
}

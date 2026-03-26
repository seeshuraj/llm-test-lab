import { authHeaders } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

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
  model_name: string;
  created_at?: string;
  avg_score: number;   // pre-computed by backend, use this directly
  results: ScenarioResult[];
}

export async function fetchRuns(): Promise<Run[]> {
  const res = await fetch(`${API_BASE}/api/runs`, { headers: authHeaders() });
  if (res.status === 401) throw new Error("UNAUTHORIZED");
  if (!res.ok) throw new Error("Failed to fetch runs");
  return res.json();
}

export async function fetchRun(runId: string): Promise<Run> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}`, { headers: authHeaders() });
  if (res.status === 401) throw new Error("UNAUTHORIZED");
  if (!res.ok) throw new Error("Failed to fetch run");
  return res.json();
}

export async function deleteRun(runId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to delete run");
}

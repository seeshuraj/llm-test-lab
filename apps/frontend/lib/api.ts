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
  avg_score: number;
  results: ScenarioResult[];
  scenarios_yaml?: string;
  rubric?: string;
  app_endpoint_url?: string;
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

export async function fetchSharedRun(runId: string): Promise<Run> {
  const res = await fetch(`${API_BASE}/api/share/${runId}`);
  if (!res.ok) throw new Error("Run not found");
  return res.json();
}

export async function deleteRun(runId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to delete run");
}

export async function rerunRun(runId: string): Promise<Run> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/rerun`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (res.status === 401) throw new Error("UNAUTHORIZED");
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Re-run failed");
  }
  return res.json();
}

export async function fetchModels(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/models`);
  if (!res.ok) return ["llama-3.1-8b-instant"];
  const data = await res.json();
  return data.models;
}

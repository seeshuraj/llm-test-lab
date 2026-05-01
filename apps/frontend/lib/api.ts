import { getToken, authHeaders } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface ScenarioResult {
  scenario_id: string;
  score: number;
  latency_ms: number;
  judge_model: string;
  reason: string;
  // RAG metrics (optional — populated when run via RAG pipeline)
  faithfulness?: number;
  context_precision?: number;
  answer_relevance?: number;
}

export interface Run {
  run_id: string;
  project: string;
  variant_name: string;
  model_name: string;
  run_label?: string;
  created_at?: string;
  avg_score: number;
  results: ScenarioResult[];
}

/** Enriched model info returned by the backend. */
export interface ModelDetail {
  id: string;
  provider: "groq" | "openai" | "ollama" | "unknown";
  display_name?: string;
}

// ─── Runs ────────────────────────────────────────────────────────────────────

export async function fetchRuns(): Promise<Run[]> {
  const res = await fetch(`${API_BASE}/api/runs`, { headers: authHeaders() });
  if (res.status === 401) throw new Error("UNAUTHORIZED");
  if (!res.ok) throw new Error(`Failed to fetch runs: ${res.status}`);
  return res.json();
}

export async function fetchRun(id: string): Promise<Run> {
  const res = await fetch(`${API_BASE}/api/runs/${id}`, { headers: authHeaders() });
  if (res.status === 401) throw new Error("UNAUTHORIZED");
  if (!res.ok) throw new Error(`Failed to fetch run: ${res.status}`);
  return res.json();
}

export async function deleteRun(runId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Delete failed");
}

export async function rerunRun(runId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/rerun`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Re-run failed");
}

export async function updateRunLabel(runId: string, label: string): Promise<Run> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/label`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ label }),
  });
  if (!res.ok) throw new Error("Label update failed");
  return res.json();
}

// ─── Models ──────────────────────────────────────────────────────────────────

/**
 * Fetches available models from the backend.
 * The backend may return either:
 *   - string[]            (legacy)  → wrapped into ModelDetail[]
 *   - ModelDetail[]       (current) → used as-is
 */
export async function fetchModels(): Promise<ModelDetail[]> {
  try {
    const res = await fetch(`${API_BASE}/api/models`, { headers: authHeaders() });
    if (!res.ok) throw new Error("models fetch failed");
    const data = await res.json();

    // Normalise legacy string[] responses
    if (Array.isArray(data) && data.length > 0 && typeof data[0] === "string") {
      return (data as string[]).map(inferModelDetail);
    }
    return data as ModelDetail[];
  } catch {
    // Hardcoded fallback so the UI is never empty
    return [
      { id: "llama-3.1-8b-instant", provider: "groq" },
      { id: "llama3-70b-8192", provider: "groq" },
      { id: "gpt-4o-mini", provider: "openai" },
      { id: "gpt-4o", provider: "openai" },
    ];
  }
}

/** Infer provider from model id string. */
function inferModelDetail(id: string): ModelDetail {
  if (id.startsWith("gpt-") || id.startsWith("o1") || id.startsWith("o3")) {
    return { id, provider: "openai" };
  }
  if (id.includes("llama") || id.includes("mixtral") || id.includes("gemma") || id.includes("deepseek")) {
    return { id, provider: "groq" };
  }
  if (id.includes("ollama") || id.startsWith("local/")) {
    return { id, provider: "ollama" };
  }
  return { id, provider: "unknown" };
}

// ─── CSV Export ──────────────────────────────────────────────────────────────

export function exportRunCSV(run: Run): void {
  const header = ["scenario_id", "score", "latency_ms", "judge_model", "faithfulness", "context_precision", "answer_relevance", "reason"];
  const rows = run.results.map((r) => [
    r.scenario_id,
    r.score,
    r.latency_ms,
    r.judge_model,
    r.faithfulness ?? "",
    r.context_precision ?? "",
    r.answer_relevance ?? "",
    `"${r.reason.replace(/"/g, "'")}"`
  ]);
  const csv = [header, ...rows].map((row) => row.join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `run-${run.run_id.slice(0, 8)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

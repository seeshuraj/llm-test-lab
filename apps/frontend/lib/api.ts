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
  is_public?: boolean;
  results: ScenarioResult[] | null;
}

/** Enriched model info returned by the backend. */
export interface ModelDetail {
  id: string;
  provider: "groq" | "openai" | "ollama" | "anthropic" | "unknown";
  display_name?: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Normalize a raw run object from the backend.
 *  Backend returns { id, mean_score, ... } — frontend expects { run_id, avg_score, ... }.
 *  Also coerce null results to empty array. */
function normalizeRun(r: any): Run {
  return {
    ...r,
    // Backend uses `id`; frontend uses `run_id`
    run_id: r.run_id ?? r.id,
    // Backend uses `mean_score`; frontend uses `avg_score`
    avg_score: r.avg_score ?? r.mean_score ?? 0,
    results: r.results ?? [],
    is_public: r.is_public ?? false,
  };
}

// ─── Runs ────────────────────────────────────────────────────────────────────

export async function fetchRuns(): Promise<Run[]> {
  const res = await fetch(`${API_BASE}/api/runs`, { headers: authHeaders() });
  if (res.status === 401) throw new Error("UNAUTHORIZED");
  if (!res.ok) throw new Error(`Failed to fetch runs: ${res.status}`);
  const data = await res.json();
  return (data as any[]).map(normalizeRun);
}

export async function fetchRun(id: string): Promise<Run> {
  const res = await fetch(`${API_BASE}/api/runs/${id}`, { headers: authHeaders() });
  if (res.status === 401) throw new Error("UNAUTHORIZED");
  if (!res.ok) throw new Error(`Failed to fetch run: ${res.status}`);
  return normalizeRun(await res.json());
}

/**
 * Fetch a publicly shared run — no auth required.
 * Used by /share/[runId] which is a public report page.
 * Backend: GET /api/runs/{run_id}/share (is_public must be true)
 */
export async function fetchSharedRun(runId: string): Promise<Run> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/share`);
  if (res.status === 404) throw new Error("Run not found or not shared publicly");
  if (!res.ok) throw new Error(`Failed to fetch shared run: ${res.status}`);
  return normalizeRun(await res.json());
}

export async function deleteRun(runId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Delete failed");
}

/**
 * Re-run an existing run. Returns the newly created Run so the caller
 * can navigate directly to its detail page (graphs + explanations).
 * Backend returns RunOut with `id` field — normalizeRun maps it to `run_id`.
 */
export async function rerunRun(runId: string): Promise<Run> {
  if (!runId) throw new Error("Invalid run ID");
  const res = await fetch(`${API_BASE}/api/runs/${runId}/rerun`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Re-run failed (${res.status})`);
  }
  return normalizeRun(await res.json());
}

export async function updateRunLabel(runId: string, label: string): Promise<Run> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/label`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ label }),
  });
  if (!res.ok) throw new Error("Label update failed");
  return normalizeRun(await res.json());
}

/**
 * Toggle the is_public flag on a run.
 * Called by the Share button before copying the link.
 */
export async function toggleRunPublic(runId: string, isPublic: boolean): Promise<void> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/share`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ is_public: isPublic }),
  });
  if (!res.ok) throw new Error("Failed to update share status");
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

    // Backend returns { id, name, provider, ... } — map to ModelDetail shape
    return (data as any[]).map((m) => ({
      id: m.id,
      provider: (m.provider ?? "unknown").toLowerCase() as ModelDetail["provider"],
      display_name: m.name ?? m.display_name,
    }));
  } catch {
    // Hardcoded fallback so the UI is never empty
    return [
      { id: "llama-3.1-8b-instant", provider: "groq" },
      { id: "llama3-70b-8192",       provider: "groq" },
      { id: "gpt-4o-mini",           provider: "openai" },
      { id: "gpt-4o",               provider: "openai" },
      { id: "claude-3-5-haiku-20241022", provider: "anthropic" },
      { id: "claude-3-5-sonnet-20241022", provider: "anthropic" },
    ];
  }
}

/** Infer provider from model id string. */
function inferModelDetail(id: string): ModelDetail {
  if (id.startsWith("claude")) {
    return { id, provider: "anthropic" };
  }
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
  const rows = (run.results ?? []).map((r) => [
    r.scenario_id,
    r.score,
    r.latency_ms,
    r.judge_model,
    r.faithfulness ?? "",
    r.context_precision ?? "",
    r.answer_relevance ?? "",
    `"${r.reason.replace(/"/g, "'")}"`,
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

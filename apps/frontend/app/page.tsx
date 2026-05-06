"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { fetchRuns, deleteRun, rerunRun, fetchModels, exportRunCSV, updateRunLabel, Run, ModelDetail } from "@/lib/api";
import { getToken, clearToken, authHeaders } from "@/lib/auth";
import {
  listSavedScenarios, saveScenario, deleteScenario, SavedScenario,
} from "@/lib/scenario-library";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const POLL_INTERVAL_MS = 30_000;

const SAMPLE_YAML = `scenarios:
  - id: my-first-test
    question: "What is the capital of France?"
    context_docs:
      - "France is a country in Western Europe. Its capital city is Paris."
    expected_keywords: ["Paris"]

  - id: second-test
    question: "What causes rain?"
    context_docs:
      - "Rain is caused by water vapour in the atmosphere condensing into droplets."
    expected_keywords: ["water", "condensing"]
`;

const DEFAULT_RUBRIC_TEXT = `Score the answer based on correctness and grounding in the provided context.
Rules:
(1) If the context contains relevant information, the answer must use it accurately.
(2) If the context does NOT contain relevant information, a correct refusal should score 0.85+.
(3) If the context is irrelevant but the model answers from general knowledge, score 0.3-0.5.
(4) Penalise any answer that contradicts the context.`;

const scoreColor = (s: number) =>
  s >= 0.8 ? "#10b981" : s >= 0.5 ? "#f59e0b" : "#ef4444";

function resolveStatColor(color: string): string {
  return color.startsWith("#") ? color : "#ffffff";
}

// ─── Provider badge ──────────────────────────────────────────────────────────

const PROVIDER_META: Record<string, { label: string; color: string }> = {
  groq:      { label: "Groq",      color: "#f55036" },
  anthropic: { label: "Anthropic", color: "#c5693a" },
  openai:    { label: "OpenAI",    color: "#10a37f" },
  ollama:    { label: "Ollama",    color: "#7c3aed" },
  unknown:   { label: "?",         color: "#6b7280" },
};

function ProviderBadge({ provider }: { provider: string }) {
  const meta = PROVIDER_META[provider] ?? PROVIDER_META.unknown;
  return (
    <span
      className="inline-block text-white text-xs font-semibold px-1.5 py-0.5 rounded"
      style={{ backgroundColor: meta.color, fontSize: "0.65rem", lineHeight: 1.4 }}
    >
      {meta.label}
    </span>
  );
}

export default function HomePage() {
  const router = useRouter();
  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [rerunning, setRerunning] = useState<string | null>(null);

  const [editingLabel, setEditingLabel] = useState<string | null>(null);
  const [editLabelValue, setEditLabelValue] = useState("");
  const [savingLabel, setSavingLabel] = useState<string | null>(null);

  const [project, setProject] = useState("demo-project");
  const [variant, setVariant] = useState("v1");
  const [runLabel, setRunLabel] = useState("");
  const [modelName, setModelName] = useState("llama-3.1-8b-instant");
  const [availableModels, setAvailableModels] = useState<ModelDetail[]>([
    { id: "llama-3.1-8b-instant", provider: "groq" },
  ]);
  const [isPro, setIsPro] = useState(false);
  const [scenariosYaml, setScenariosYaml] = useState("");
  const [fileName, setFileName] = useState("");
  const [yamlMode, setYamlMode] = useState<"file" | "editor">("editor");
  const [appUrl, setAppUrl] = useState("");
  const [rubric, setRubric] = useState("");
  const [showRubric, setShowRubric] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  const [savedScenarios, setSavedScenarios] = useState<SavedScenario[]>([]);
  const [saveLibName, setSaveLibName] = useState("");
  const [showSaveLib, setShowSaveLib] = useState(false);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!getToken()) router.push("/login");
  }, []);

  useEffect(() => {
    setSavedScenarios(listSavedScenarios());
    fetchModels().then(setAvailableModels);
    // Fetch plan status to gate Pro models — corrected path to /api/auth/me
    fetch(`${API_BASE}/api/auth/me`, { headers: authHeaders() })
      .then((r) => r.json())
      .then((d) => setIsPro(!!d.is_pro))
      .catch(() => {});
  }, []);

  const silentRefresh = useCallback(() => {
    if (!getToken()) return;
    setRefreshing(true);
    fetchRuns()
      .then((data) => { setRuns(data); setLastUpdated(new Date()); setError(null); })
      .catch((e) => {
        if (String(e).includes("UNAUTHORIZED")) { clearToken(); router.push("/login"); }
      })
      .finally(() => setRefreshing(false));
  }, []);

  const loadRuns = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    fetchRuns()
      .then((data) => { setRuns(data); setLastUpdated(new Date()); setError(null); })
      .catch((e) => {
        if (String(e).includes("UNAUTHORIZED")) { clearToken(); router.push("/login"); }
        else setError(String(e));
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!getToken()) return;
    loadRuns();
    intervalRef.current = setInterval(silentRefresh, POLL_INTERVAL_MS);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, []);

  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === "visible" && getToken()) silentRefresh();
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, []);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (ev) => setScenariosYaml(ev.target?.result as string);
    reader.readAsText(file);
  };

  const handleCopyShareLink = (runId: string) => {
    const url = `${window.location.origin}/share/${runId}`;
    navigator.clipboard.writeText(url).then(() => {
      setCopied(runId);
      setTimeout(() => setCopied(null), 2000);
    });
  };

  const handleSaveToLibrary = () => {
    const name = saveLibName.trim();
    if (!name || !scenariosYaml.trim()) return;
    saveScenario(name, scenariosYaml);
    setSavedScenarios(listSavedScenarios());
    setSaveLibName("");
    setShowSaveLib(false);
  };

  const handleLoadFromLibrary = (yaml: string) => {
    setScenariosYaml(yaml);
    setYamlMode("editor");
  };

  const handleDeleteFromLibrary = (name: string) => {
    deleteScenario(name);
    setSavedScenarios(listSavedScenarios());
  };

  const handleRerun = async (runId: string) => {
    setRerunning(runId);
    try {
      await rerunRun(runId);
      loadRuns();
    } catch (e) {
      alert(`Re-run failed: ${e}`);
    } finally {
      setRerunning(null);
    }
  };

  const handleSaveLabel = async (runId: string) => {
    setSavingLabel(runId);
    try {
      const updated = await updateRunLabel(runId, editLabelValue);
      setRuns((prev) => prev.map((r) => r.run_id === runId ? { ...r, run_label: updated.run_label } : r));
      setEditingLabel(null);
    } catch {
      alert("Failed to save label");
    } finally {
      setSavingLabel(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const yaml = scenariosYaml.trim();
    if (!yaml) { setFormError("Please enter or upload a scenarios YAML"); return; }
    setSubmitting(true);
    setFormError(null);
    try {
      const res = await fetch(`${API_BASE}/api/run-local`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          scenarios_yaml: yaml,
          project,
          variant_name: variant,
          model_name: modelName,
          run_label: runLabel.trim() || null,
          app_endpoint_url: appUrl || null,
          rubric: rubric.trim() || null,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        // Surface Pro upgrade hint on 403
        if (res.status === 402 || res.status === 403) {
          throw new Error(err.detail + " → Go to Settings to upgrade.");
        }
        throw new Error(err.detail || "Run failed");
      }
      setShowForm(false);
      setScenariosYaml(""); setFileName(""); setRubric(""); setRunLabel("");
      loadRuns();
    } catch (e) {
      setFormError(String(e));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (runId: string) => {
    if (!confirm("Delete this run? This cannot be undone.")) return;
    try { await deleteRun(runId); loadRuns(); }
    catch { alert("Failed to delete run"); }
  };

  const totalRuns = runs.length;
  // Guard: r.results may be undefined for pending/errored runs
  const allScores = runs.flatMap((r) => (r.results ?? []).map((x) => x.score));
  const overallAvg = allScores.length ? allScores.reduce((a, b) => a + b, 0) / allScores.length : null;
  const passRate = allScores.length ? (allScores.filter((s) => s >= 0.8).length / allScores.length) * 100 : null;
  const projects = Array.from(new Set(runs.map((r) => r.project)));
  const sparkData = [...runs]
    .sort((a, b) => (a.created_at ?? "").localeCompare(b.created_at ?? ""))
    .slice(-10)
    .map((r) => ({
      t: r.run_label || (r.created_at ? new Date(r.created_at).toLocaleDateString() : r.run_id.slice(0, 6)),
      avg: r.avg_score,
    }));

  const selectedModel = availableModels.find((m) => m.id === modelName);
  const ANTHROPIC_PROVIDERS = ["anthropic"];
  const isProModel = (m: ModelDetail) => ANTHROPIC_PROVIDERS.includes(m.provider.toLowerCase());

  return (
    <main className="max-w-6xl mx-auto p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">LLM Test Lab</h1>
          <div className="flex items-center gap-3 mt-1">
            <p className="text-gray-400 text-sm">Evaluation dashboard</p>
            {lastUpdated && (
              <span className="flex items-center gap-1.5 text-xs text-gray-600">
                {refreshing
                  ? <span className="inline-block w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
                  : <span className="inline-block w-2 h-2 rounded-full bg-green-500" />}
                {refreshing ? "Refreshing…" : `Updated ${lastUpdated.toLocaleTimeString()}`}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {isPro && (
            <span className="bg-emerald-900/50 text-emerald-300 border border-emerald-700 text-xs font-bold px-2.5 py-1 rounded-full">PRO ✓</span>
          )}
          <Link href="/trends" className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">📈 Trends</Link>
          <Link href="/compare" className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">⚖ Compare</Link>
          <Link href="/settings" className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">⚙ Settings</Link>
          <button onClick={() => silentRefresh()} title="Refresh now" className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-2 rounded-lg text-sm transition-colors">{refreshing ? "⟳" : "↻"}</button>
          <button onClick={() => { setShowForm(true); setScenariosYaml(SAMPLE_YAML); }} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">+ New Run</button>
          <button onClick={() => { clearToken(); router.push("/login"); }} className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">Sign Out</button>
        </div>
      </div>

      {!loading && runs.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            { label: "Total Runs", value: totalRuns, color: "#ffffff" },
            { label: "Overall Avg Score", value: overallAvg !== null ? overallAvg.toFixed(2) : "—", color: overallAvg !== null ? scoreColor(overallAvg) : "#9ca3af" },
            { label: "Pass Rate (≥0.8)", value: passRate !== null ? `${passRate.toFixed(0)}%` : "—", color: passRate !== null ? scoreColor(passRate / 100) : "#9ca3af" },
            { label: "Projects", value: projects.length, color: "#ffffff" },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-gray-900 border border-gray-700 rounded-xl p-4 text-center">
              <p className="text-xs text-gray-500 mb-1">{label}</p>
              <p className="text-3xl font-bold" style={{ color: resolveStatColor(color) }}>
                {String(value)}
              </p>
            </div>
          ))}
        </div>
      )}

      {!loading && sparkData.length >= 2 && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-8">
          <h2 className="text-sm font-semibold text-gray-300 mb-3">Recent Score Trend (last {sparkData.length} runs)</h2>
          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={sparkData} margin={{ top: 5, right: 20, left: -30, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="t" tick={{ fontSize: 10, fill: "#6b7280" }} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: "#6b7280" }} tickFormatter={(v) => v.toFixed(1)} />
              <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 12 }}
                formatter={(v: any) => [Number(v).toFixed(3), "Avg Score"]} />
              <Line type="monotone" dataKey="avg" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3, fill: "#3b82f6" }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold text-white mb-4">New Evaluation Run</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Run label <span className="text-gray-600">(optional)</span></label>
                <input type="text" value={runLabel} onChange={(e) => setRunLabel(e.target.value)}
                  placeholder="e.g. GPT-4 baseline, Tuesday QA test"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Project name</label>
                  <input type="text" value={project} onChange={(e) => setProject(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Variant</label>
                  <input type="text" value={variant} onChange={(e) => setVariant(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
                </div>
              </div>

              {/* ── Model picker with Pro gating ── */}
              <div>
                <label className="block text-sm text-gray-400 mb-1">Judge model</label>
                <div className="relative">
                  <select
                    value={modelName}
                    onChange={(e) => setModelName(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500 appearance-none pr-8"
                  >
                    {availableModels.map((m) => {
                      const locked = isProModel(m) && !isPro;
                      return (
                        <option key={m.id} value={m.id} disabled={locked}>
                          {locked ? `🔒 ${m.id} (Pro only)` : m.id}
                        </option>
                      );
                    })}
                  </select>
                  <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400 text-xs">▾</div>
                </div>
                {selectedModel && (
                  <div className="mt-1.5 flex items-center gap-2">
                    <ProviderBadge provider={selectedModel.provider} />
                    {isProModel(selectedModel) && !isPro ? (
                      <span className="text-xs text-amber-400">
                        Pro only —{" "}
                        <Link href="/settings" className="underline hover:text-amber-300">Upgrade to unlock</Link>
                      </span>
                    ) : (
                      <span className="text-xs text-gray-500">
                        {selectedModel.provider === "groq" && "Fast inference via Groq Cloud"}
                        {selectedModel.provider === "anthropic" && "Claude model via Anthropic API"}
                        {selectedModel.provider === "openai" && "OpenAI API — billed per token"}
                        {selectedModel.provider === "ollama" && "Local model via Ollama"}
                        {selectedModel.provider === "unknown" && "Unknown provider"}
                      </span>
                    )}
                  </div>
                )}
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">App endpoint URL <span className="text-gray-600">(optional)</span></label>
                <input type="text" value={appUrl} onChange={(e) => setAppUrl(e.target.value)}
                  placeholder="https://your-app.com/api/query"
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-sm text-gray-400">Scenarios YAML</label>
                  <div className="flex gap-2">
                    <button type="button" onClick={() => setYamlMode("editor")}
                      className={`text-xs px-2 py-0.5 rounded ${yamlMode === "editor" ? "bg-blue-600 text-white" : "bg-gray-700 text-gray-400"}`}>Editor</button>
                    <button type="button" onClick={() => setYamlMode("file")}
                      className={`text-xs px-2 py-0.5 rounded ${yamlMode === "file" ? "bg-blue-600 text-white" : "bg-gray-700 text-gray-400"}`}>Upload file</button>
                  </div>
                </div>
                {yamlMode === "editor" ? (
                  <textarea value={scenariosYaml} onChange={(e) => setScenariosYaml(e.target.value)}
                    rows={10} className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-xs font-mono focus:outline-none focus:border-blue-500" />
                ) : (
                  <div className="flex items-center gap-3">
                    <label className="cursor-pointer bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm">
                      Choose file
                      <input type="file" accept=".yaml,.yml" onChange={handleFileUpload} className="hidden" />
                    </label>
                    {fileName && <span className="text-sm text-gray-400">{fileName}</span>}
                  </div>
                )}
              </div>

              {/* Scenario library */}
              {savedScenarios.length > 0 && (
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Load from library</label>
                  <div className="flex flex-wrap gap-2">
                    {savedScenarios.map((s) => (
                      <div key={s.name} className="flex items-center gap-1 bg-gray-800 border border-gray-700 rounded-lg px-2 py-1">
                        <button type="button" onClick={() => handleLoadFromLibrary(s.yaml)}
                          className="text-xs text-blue-400 hover:text-blue-300">{s.name}</button>
                        <button type="button" onClick={() => handleDeleteFromLibrary(s.name)}
                          className="text-xs text-gray-600 hover:text-red-400 ml-1">×</button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Save to library */}
              {scenariosYaml.trim() && (
                <div>
                  {showSaveLib ? (
                    <div className="flex gap-2">
                      <input type="text" value={saveLibName} onChange={(e) => setSaveLibName(e.target.value)}
                        placeholder="Scenario set name"
                        className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-white text-sm focus:outline-none focus:border-blue-500" />
                      <button type="button" onClick={handleSaveToLibrary}
                        className="bg-blue-600 hover:bg-blue-500 text-white px-3 py-1.5 rounded-lg text-sm">Save</button>
                      <button type="button" onClick={() => setShowSaveLib(false)}
                        className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-1.5 rounded-lg text-sm">Cancel</button>
                    </div>
                  ) : (
                    <button type="button" onClick={() => setShowSaveLib(true)}
                      className="text-xs text-gray-500 hover:text-gray-300">+ Save to library</button>
                  )}
                </div>
              )}

              {/* Rubric */}
              <div>
                <button type="button" onClick={() => { setShowRubric(!showRubric); if (!rubric) setRubric(DEFAULT_RUBRIC_TEXT); }}
                  className="text-xs text-gray-500 hover:text-gray-300">
                  {showRubric ? "▾ Hide custom rubric" : "▸ Add custom rubric (optional)"}
                </button>
                {showRubric && (
                  <textarea value={rubric} onChange={(e) => setRubric(e.target.value)}
                    rows={5} className="mt-2 w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-xs font-mono focus:outline-none focus:border-blue-500" />
                )}
              </div>

              {formError && <p className="text-red-400 text-sm">{formError}</p>}

              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={submitting}
                  className="flex-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white py-2.5 rounded-lg font-medium text-sm transition-colors">
                  {submitting ? "Running…" : "Run Evaluation"}
                </button>
                <button type="button" onClick={() => { setShowForm(false); setFormError(null); }}
                  className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2.5 rounded-lg text-sm transition-colors">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-20">
          <div className="text-gray-500 text-sm">Loading runs…</div>
        </div>
      )}

      {!loading && error && (
        <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 mb-6">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {!loading && !error && runs.length === 0 && (
        <div className="text-center py-20">
          <p className="text-gray-500 text-sm mb-4">No evaluation runs yet.</p>
          <button onClick={() => { setShowForm(true); setScenariosYaml(SAMPLE_YAML); }}
            className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors">
            Start your first run
          </button>
        </div>
      )}

      {!loading && runs.length > 0 && (
        <div className="space-y-4">
          {runs.map((run) => {
            const results = run.results ?? [];
            const scores = results.map((x) => x.score);
            const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null;
            const pass = scores.filter((s) => s >= 0.8).length;
            return (
              <div key={run.run_id} className="bg-gray-900 border border-gray-700 rounded-xl p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      {editingLabel === run.run_id ? (
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            value={editLabelValue}
                            onChange={(e) => setEditLabelValue(e.target.value)}
                            onKeyDown={(e) => { if (e.key === "Enter") handleSaveLabel(run.run_id); if (e.key === "Escape") setEditingLabel(null); }}
                            className="bg-gray-800 border border-blue-500 rounded px-2 py-0.5 text-white text-sm focus:outline-none w-48"
                            autoFocus
                          />
                          <button onClick={() => handleSaveLabel(run.run_id)} disabled={savingLabel === run.run_id}
                            className="text-xs text-blue-400 hover:text-blue-300 disabled:opacity-50">
                            {savingLabel === run.run_id ? "Saving…" : "Save"}
                          </button>
                          <button onClick={() => setEditingLabel(null)} className="text-xs text-gray-500 hover:text-gray-300">Cancel</button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5">
                          <h3 className="font-semibold text-white text-sm">
                            {run.run_label || run.project}
                          </h3>
                          <button
                            onClick={() => { setEditingLabel(run.run_id); setEditLabelValue(run.run_label || ""); }}
                            className="text-gray-600 hover:text-gray-400 text-xs"
                            title="Edit label"
                          >✎</button>
                        </div>
                      )}
                      <span className="text-xs text-gray-600">{run.variant_name}</span>
                      {run.model_name && (
                        <span className="text-xs bg-gray-800 border border-gray-700 rounded px-1.5 py-0.5 text-gray-400 font-mono">{run.model_name}</span>
                      )}
                    </div>
                    <p className="text-xs text-gray-600 mt-0.5">
                      {run.created_at ? new Date(run.created_at).toLocaleString() : run.run_id}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {avg !== null && (
                      <span className="text-2xl font-bold" style={{ color: scoreColor(avg) }}>
                        {avg.toFixed(2)}
                      </span>
                    )}
                    <div className="flex flex-col gap-1">
                      <button onClick={() => handleCopyShareLink(run.run_id)}
                        className="text-xs bg-gray-700 hover:bg-gray-600 text-gray-300 px-2 py-1 rounded transition-colors">
                        {copied === run.run_id ? "✓ Copied" : "Share"}
                      </button>
                      <button onClick={() => handleRerun(run.run_id)} disabled={rerunning === run.run_id}
                        className="text-xs bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-gray-300 px-2 py-1 rounded transition-colors">
                        {rerunning === run.run_id ? "…" : "Re-run"}
                      </button>
                      <button onClick={() => handleDelete(run.run_id)}
                        className="text-xs bg-gray-700 hover:bg-red-900 text-gray-400 hover:text-red-300 px-2 py-1 rounded transition-colors">
                        Delete
                      </button>
                    </div>
                  </div>
                </div>

                {results.length > 0 && (
                  <div className="mt-4 space-y-2">
                    <div className="flex items-center gap-3 text-xs text-gray-500 mb-2">
                      <span>{results.length} scenario{results.length !== 1 ? "s" : ""}</span>
                      <span>·</span>
                      <span>{pass}/{results.length} passed</span>
                    </div>
                    {results.map((res, i) => (
                      <div key={i} className="flex items-center gap-3 bg-gray-800/50 rounded-lg px-3 py-2">
                        <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: scoreColor(res.score) }} />
                        <span className="text-xs text-gray-400 font-mono flex-1 truncate">{res.scenario_id}</span>
                        <span className="text-xs font-bold shrink-0" style={{ color: scoreColor(res.score) }}>
                          {res.score.toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </main>
  );
}

"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { fetchRuns, deleteRun, rerunRun, fetchModels, exportRunCSV, updateRunLabel, Run } from "@/lib/api";
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

export default function HomePage() {
  const router = useRouter();
  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [rerunning, setRerunning] = useState<string | null>(null);

  // Inline label editing
  const [editingLabel, setEditingLabel] = useState<string | null>(null);
  const [editLabelValue, setEditLabelValue] = useState("");
  const [savingLabel, setSavingLabel] = useState<string | null>(null);

  // Form state
  const [project, setProject] = useState("demo-project");
  const [variant, setVariant] = useState("v1");
  const [runLabel, setRunLabel] = useState("");
  const [modelName, setModelName] = useState("llama-3.1-8b-instant");
  const [availableModels, setAvailableModels] = useState<string[]>(["llama-3.1-8b-instant"]);
  const [scenariosYaml, setScenariosYaml] = useState("");
  const [fileName, setFileName] = useState("");
  const [yamlMode, setYamlMode] = useState<"file" | "editor">("editor");
  const [appUrl, setAppUrl] = useState("");
  const [rubric, setRubric] = useState("");
  const [showRubric, setShowRubric] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  // Scenario library
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
  const allScores = runs.flatMap((r) => r.results.map((x) => x.score));
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

  return (
    <main className="max-w-6xl mx-auto p-8">
      {/* Header */}
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
          <Link href="/trends" className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">📈 Trends</Link>
          <Link href="/compare" className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">⚖ Compare</Link>
          <button onClick={() => silentRefresh()} title="Refresh now" className="bg-gray-700 hover:bg-gray-600 text-white px-3 py-2 rounded-lg text-sm transition-colors">{refreshing ? "⟳" : "↻"}</button>
          <button onClick={() => { setShowForm(true); setScenariosYaml(SAMPLE_YAML); }} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">+ New Run</button>
          <button onClick={() => { clearToken(); router.push("/login"); }} className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">Sign Out</button>
        </div>
      </div>

      {/* Stats */}
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

      {/* Spark chart */}
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

      {/* New Run Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <h2 className="text-xl font-bold text-white mb-4">New Evaluation Run</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Run label <span className="text-gray-600">(optional)</span></label>
                <input type="text" value={runLabel} onChange={(e) => setRunLabel(e.target.value)}
                  placeholder="e.g. GPT-4 baseline, Tuesday QA test"
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Project name</label>
                  <input type="text" value={project} onChange={(e) => setProject(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" required />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Variant name</label>
                  <input type="text" value={variant} onChange={(e) => setVariant(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500" required />
                </div>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Model</label>
                <select value={modelName} onChange={(e) => setModelName(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500">
                  {availableModels.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                </select>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm text-gray-400">Scenarios YAML</label>
                  <div className="flex items-center gap-2">
                    {savedScenarios.length > 0 && (
                      <select
                        onChange={(e) => { if (e.target.value) handleLoadFromLibrary(e.target.value); e.target.value = ""; }}
                        className="bg-gray-800 border border-gray-600 rounded-lg px-2 py-1 text-gray-300 text-xs focus:outline-none focus:border-blue-500"
                        defaultValue=""
                      >
                        <option value="" disabled>📚 Load saved…</option>
                        {savedScenarios.map((s) => (
                          <option key={s.name} value={s.yaml}>{s.name}</option>
                        ))}
                      </select>
                    )}
                    <div className="flex bg-gray-800 border border-gray-600 rounded-lg p-0.5 text-xs">
                      <button type="button" onClick={() => setYamlMode("editor")}
                        className={`px-3 py-1 rounded-md transition-colors ${yamlMode === "editor" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"}`}>
                        ✏️ Editor
                      </button>
                      <button type="button" onClick={() => setYamlMode("file")}
                        className={`px-3 py-1 rounded-md transition-colors ${yamlMode === "file" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"}`}>
                        📂 File
                      </button>
                    </div>
                  </div>
                </div>
                {yamlMode === "editor" ? (
                  <div className="relative">
                    <textarea value={scenariosYaml} onChange={(e) => setScenariosYaml(e.target.value)}
                      rows={10} spellCheck={false} placeholder={SAMPLE_YAML}
                      className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-xs font-mono focus:outline-none focus:border-blue-500 resize-y" />
                    <button type="button" onClick={() => setScenariosYaml(SAMPLE_YAML)}
                      className="absolute top-2 right-2 text-xs text-gray-500 hover:text-gray-300 bg-gray-900 border border-gray-700 rounded px-2 py-0.5">Load sample</button>
                  </div>
                ) : (
                  <label className="flex items-center gap-3 cursor-pointer w-full bg-gray-800 border border-gray-600 hover:border-blue-500 rounded-lg px-3 py-2 text-sm transition-colors">
                    <span className="text-blue-400">📂 Choose file</span>
                    <span className="text-gray-400 truncate">{fileName || "No file chosen"}</span>
                    <input type="file" accept=".yaml,.yml" onChange={handleFileUpload} className="hidden" />
                  </label>
                )}
                {scenariosYaml.trim() && (
                  <div className="mt-2">
                    {!showSaveLib ? (
                      <button type="button" onClick={() => setShowSaveLib(true)}
                        className="text-xs text-gray-500 hover:text-gray-300 transition-colors">+ Save to library</button>
                    ) : (
                      <div className="flex items-center gap-2">
                        <input type="text" value={saveLibName} onChange={(e) => setSaveLibName(e.target.value)}
                          placeholder="Scenario set name…"
                          className="flex-1 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-white text-xs focus:outline-none focus:border-blue-500" />
                        <button type="button" onClick={handleSaveToLibrary}
                          className="text-xs bg-blue-700 hover:bg-blue-600 text-white px-2 py-1 rounded transition-colors">Save</button>
                        <button type="button" onClick={() => setShowSaveLib(false)}
                          className="text-xs text-gray-500 hover:text-gray-300">Cancel</button>
                      </div>
                    )}
                    {savedScenarios.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {savedScenarios.map((s) => (
                          <div key={s.name} className="flex items-center justify-between text-xs text-gray-500">
                            <span>💾 {s.name}</span>
                            <button type="button" onClick={() => handleDeleteFromLibrary(s.name)}
                              className="text-red-500 hover:text-red-400">× remove</button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">App endpoint URL <span className="text-gray-600">(optional)</span></label>
                <input type="text" value={appUrl} onChange={(e) => setAppUrl(e.target.value)}
                  placeholder="https://your-app.com/answer"
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500 font-mono" />
                <p className="text-xs text-gray-500 mt-1">POST {`{ question, context }`} → expects {`{ answer }`}. Leave blank for echo mode.</p>
              </div>
              <div>
                <button type="button" onClick={() => setShowRubric(!showRubric)}
                  className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-200 transition-colors">
                  <span className={`transition-transform ${showRubric ? "rotate-90" : ""}`}>▶</span>
                  Custom rubric <span className="text-gray-600">(optional)</span>
                </button>
                {showRubric && (
                  <div className="mt-2">
                    <textarea value={rubric} onChange={(e) => setRubric(e.target.value)}
                      rows={5} placeholder={DEFAULT_RUBRIC_TEXT}
                      className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-xs font-mono focus:outline-none focus:border-blue-500 resize-y" />
                    <p className="text-xs text-gray-500 mt-1">Leave blank to use the default rubric.</p>
                  </div>
                )}
              </div>
              {formError && <p className="text-red-400 text-sm">{formError}</p>}
              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={submitting}
                  className="flex-1 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed text-white py-2 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2">
                  {submitting && (
                    <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                  )}
                  {submitting ? "Running eval..." : "Run Evaluation"}
                </button>
                <button type="button" onClick={() => { setShowForm(false); setFormError(null); setScenariosYaml(""); setFileName(""); setRubric(""); setRunLabel(""); }}
                  className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 rounded-lg text-sm font-medium transition-colors">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Runs table */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-12 bg-gray-800 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : error ? (
        <p className="text-red-400">Failed to connect: {error}</p>
      ) : runs.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-gray-500 text-lg mb-2">No runs yet.</p>
          <p className="text-gray-600 text-sm">Click &quot;+ New Run&quot; to run your first evaluation.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-700">
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-800 text-gray-300">
              <tr>
                <th className="px-4 py-3">Label / ID</th>
                <th className="px-4 py-3">Project</th>
                <th className="px-4 py-3">Variant</th>
                <th className="px-4 py-3">Model</th>
                <th className="px-4 py-3">Scenarios</th>
                <th className="px-4 py-3">Avg Score</th>
                <th className="px-4 py-3">Pass Rate</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run, i) => {
                const scores = run.results.map((r) => r.score);
                const avg = run.avg_score;
                const pass = scores.length ? (scores.filter((s) => s >= 0.8).length / scores.length) * 100 : 0;
                const isEditing = editingLabel === run.run_id;
                return (
                  <tr key={run.run_id} className={i % 2 === 0 ? "bg-gray-900" : "bg-gray-950"}>
                    <td className="px-4 py-3">
                      {isEditing ? (
                        <div className="flex items-center gap-1">
                          <input
                            autoFocus
                            type="text"
                            value={editLabelValue}
                            onChange={(e) => setEditLabelValue(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") handleSaveLabel(run.run_id);
                              if (e.key === "Escape") setEditingLabel(null);
                            }}
                            className="bg-gray-800 border border-blue-500 rounded px-2 py-0.5 text-white text-xs w-36 focus:outline-none"
                          />
                          <button onClick={() => handleSaveLabel(run.run_id)} disabled={savingLabel === run.run_id}
                            className="text-green-400 hover:text-green-300 text-xs disabled:opacity-50">
                            {savingLabel === run.run_id ? "…" : "✓"}
                          </button>
                          <button onClick={() => setEditingLabel(null)} className="text-gray-500 hover:text-gray-300 text-xs">✕</button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 group">
                          {run.run_label
                            ? <span className="text-white font-medium text-sm">{run.run_label}</span>
                            : <span className="font-mono text-xs text-gray-400">{run.run_id.slice(0, 8)}…</span>
                          }
                          <button
                            onClick={() => { setEditingLabel(run.run_id); setEditLabelValue(run.run_label || ""); }}
                            className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-gray-300 text-xs transition-opacity ml-1"
                            title="Rename"
                          >✏️</button>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-white">{run.project}</td>
                    <td className="px-4 py-3 text-gray-300">{run.variant_name}</td>
                    <td className="px-4 py-3 text-gray-400 text-xs font-mono">{run.model_name}</td>
                    <td className="px-4 py-3 text-gray-300">{run.results.length}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                          <div className="h-full rounded-full" style={{ width: `${avg * 100}%`, backgroundColor: scoreColor(avg) }} />
                        </div>
                        <span className="font-bold text-xs" style={{ color: scoreColor(avg) }}>{avg.toFixed(2)}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                        pass >= 80 ? "bg-green-900 text-green-300" : pass >= 50 ? "bg-yellow-900 text-yellow-300" : "bg-red-900 text-red-300"
                      }`}>{pass.toFixed(0)}%</span>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{run.created_at ? new Date(run.created_at).toLocaleString() : "—"}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <Link href={`/runs/${run.run_id}`} className="text-blue-400 hover:underline text-xs">View →</Link>
                        <button onClick={() => handleRerun(run.run_id)} disabled={rerunning === run.run_id}
                          title="Re-run" className="text-xs text-green-400 hover:text-green-300 disabled:opacity-40 transition-colors">
                          {rerunning === run.run_id ? "⏳" : "🔁"}
                        </button>
                        <button onClick={() => exportRunCSV(run)} title="Export CSV"
                          className="text-xs text-gray-400 hover:text-white transition-colors">⬇️</button>
                        <button onClick={() => handleCopyShareLink(run.run_id)} title="Copy shareable link"
                          className="text-xs text-gray-400 hover:text-white transition-colors">
                          {copied === run.run_id ? "✅" : "🔗"}
                        </button>
                        <button onClick={() => handleDelete(run.run_id)} className="text-red-500 hover:text-red-400 text-xs transition-colors">🗑</button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}

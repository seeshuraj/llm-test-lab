"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { fetchRuns, deleteRun, Run } from "@/lib/api";
import { getToken, clearToken, authHeaders } from "@/lib/auth";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

const scoreColor = (s: number) =>
  s >= 0.8 ? "#10b981" : s >= 0.5 ? "#f59e0b" : "#ef4444";

export default function HomePage() {
  const router = useRouter();
  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const [project, setProject] = useState("demo-project");
  const [variant, setVariant] = useState("v1");
  const [scenariosYaml, setScenariosYaml] = useState("");
  const [fileName, setFileName] = useState("");
  const [appUrl, setAppUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) router.push("/login");
  }, []);

  const loadRuns = () => {
    setLoading(true);
    fetchRuns()
      .then(setRuns)
      .catch((e) => {
        if (String(e).includes("UNAUTHORIZED")) {
          clearToken();
          router.push("/login");
        } else {
          setError(String(e));
        }
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (getToken()) loadRuns();
  }, []);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (ev) => setScenariosYaml(ev.target?.result as string);
    reader.readAsText(file);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scenariosYaml) { setFormError("Please upload a scenarios.yaml file"); return; }
    setSubmitting(true);
    setFormError(null);
    try {
      const res = await fetch(`${API_BASE}/api/run-local`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          scenarios_yaml: scenariosYaml,
          project,
          variant_name: variant,
          app_endpoint_url: appUrl || null,  // matches backend RunLocalRequest
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Run failed");
      }
      setShowForm(false);
      setScenariosYaml("");
      setFileName("");
      loadRuns();
    } catch (e) {
      setFormError(String(e));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (runId: string) => {
    if (!confirm("Delete this run? This cannot be undone.")) return;
    try {
      await deleteRun(runId);
      loadRuns();
    } catch (e) {
      alert("Failed to delete run");
    }
  };

  // --- Summary stats ---
  const totalRuns = runs.length;
  const allScores = runs.flatMap((r) => r.results.map((x) => x.score));
  const overallAvg = allScores.length
    ? allScores.reduce((a, b) => a + b, 0) / allScores.length
    : null;
  const passRate = allScores.length
    ? (allScores.filter((s) => s >= 0.8).length / allScores.length) * 100
    : null;
  const projects = Array.from(new Set(runs.map((r) => r.project)));

  const sparkData = [...runs]
    .sort((a, b) => (a.created_at ?? "").localeCompare(b.created_at ?? ""))
    .slice(-10)
    .map((r) => ({
      t: r.created_at ? new Date(r.created_at).toLocaleDateString() : r.run_id.slice(0, 6),
      avg: r.results.length
        ? parseFloat((r.results.reduce((a, x) => a + x.score, 0) / r.results.length).toFixed(3))
        : 0,
    }));

  return (
    <main className="max-w-6xl mx-auto p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">LLM Test Lab</h1>
          <p className="text-gray-400 mt-1">Evaluation dashboard</p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/trends" className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">📈 Trends</Link>
          <Link href="/compare" className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">⚖ Compare</Link>
          <button onClick={() => setShowForm(true)} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">+ New Run</button>
          <button onClick={() => { clearToken(); router.push("/login"); }} className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">Sign Out</button>
        </div>
      </div>

      {!loading && runs.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 text-center">
            <p className="text-xs text-gray-500 mb-1">Total Runs</p>
            <p className="text-3xl font-bold text-white">{totalRuns}</p>
          </div>
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 text-center">
            <p className="text-xs text-gray-500 mb-1">Overall Avg Score</p>
            <p className="text-3xl font-bold" style={{ color: overallAvg !== null ? scoreColor(overallAvg) : "#9ca3af" }}>
              {overallAvg !== null ? overallAvg.toFixed(2) : "—"}
            </p>
          </div>
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 text-center">
            <p className="text-xs text-gray-500 mb-1">Pass Rate (≥0.8)</p>
            <p className="text-3xl font-bold" style={{ color: passRate !== null ? scoreColor(passRate / 100) : "#9ca3af" }}>
              {passRate !== null ? `${passRate.toFixed(0)}%` : "—"}
            </p>
          </div>
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 text-center">
            <p className="text-xs text-gray-500 mb-1">Projects</p>
            <p className="text-3xl font-bold text-white">{projects.length}</p>
          </div>
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
              <Tooltip
                contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 12 }}
                formatter={(v: any) => [Number(v).toFixed(3), "Avg Score"]}
              />
              <Line type="monotone" dataKey="avg" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3, fill: "#3b82f6" }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-white mb-4">New Evaluation Run</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
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
              <div>
                <label className="block text-sm text-gray-400 mb-1">Scenarios file</label>
                <label className="flex items-center gap-3 cursor-pointer w-full bg-gray-800 border border-gray-600 hover:border-blue-500 rounded-lg px-3 py-2 text-sm transition-colors">
                  <span className="text-blue-400">📂 Choose file</span>
                  <span className="text-gray-400 truncate">{fileName || "No file chosen"}</span>
                  <input type="file" accept=".yaml,.yml" onChange={handleFileUpload} className="hidden" />
                </label>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  App endpoint URL <span className="text-gray-600">(optional)</span>
                </label>
                <input type="text" value={appUrl} onChange={(e) => setAppUrl(e.target.value)}
                  placeholder="https://your-app.com/answer"
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500 font-mono" />
                <p className="text-xs text-gray-500 mt-1">
                  POST {`{ question }`} → expects {`{ answer }`}. Leave blank for echo mode.
                </p>
              </div>
              {formError && <p className="text-red-400 text-sm">{formError}</p>}
              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={submitting}
                  className="flex-1 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed text-white py-2 rounded-lg text-sm font-medium transition-colors">
                  {submitting ? "Running eval..." : "Run Evaluation"}
                </button>
                <button type="button" onClick={() => { setShowForm(false); setFormError(null); setScenariosYaml(""); setFileName(""); }}
                  className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 rounded-lg text-sm font-medium transition-colors">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-gray-400">Loading runs...</p>
      ) : error ? (
        <p className="text-red-400">Failed to connect: {error}</p>
      ) : runs.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-gray-500 text-lg mb-2">No runs yet.</p>
          <p className="text-gray-600 text-sm">Click "+ New Run" to run your first evaluation.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-700">
          <table className="w-full text-sm text-left">
            <thead className="bg-gray-800 text-gray-300">
              <tr>
                <th className="px-4 py-3">Run ID</th>
                <th className="px-4 py-3">Project</th>
                <th className="px-4 py-3">Variant</th>
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
                const avg = scores.length
                  ? scores.reduce((a, b) => a + b, 0) / scores.length
                  : 0;
                const pass = scores.length
                  ? (scores.filter((s) => s >= 0.8).length / scores.length) * 100
                  : 0;
                return (
                  <tr key={run.run_id} className={i % 2 === 0 ? "bg-gray-900" : "bg-gray-950"}>
                    <td className="px-4 py-3 font-mono text-xs text-gray-400">{run.run_id.slice(0, 8)}…</td>
                    <td className="px-4 py-3 text-white">{run.project}</td>
                    <td className="px-4 py-3 text-gray-300">{run.variant_name}</td>
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
                        pass >= 80 ? "bg-green-900 text-green-300" :
                        pass >= 50 ? "bg-yellow-900 text-yellow-300" :
                        "bg-red-900 text-red-300"
                      }`}>{pass.toFixed(0)}%</span>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">
                      {run.created_at ? new Date(run.created_at).toLocaleString() : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <Link href={`/runs/${run.run_id}`} className="text-blue-400 hover:underline text-xs">View →</Link>
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

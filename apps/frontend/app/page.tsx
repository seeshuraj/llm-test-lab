"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { fetchRuns, deleteRun, Run } from "@/lib/api";
import { getToken, clearToken, authHeaders } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export default function HomePage() {
  const router = useRouter();
  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const [project, setProject] = useState("demo-project");
  const [variant, setVariant] = useState("v1");
  const [scenariosPath, setScenariosPath] = useState("");
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      const res = await fetch(`${API_BASE}/api/run-local`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          scenarios_path: scenariosPath,
          project,
          variant_name: variant,
          app_url: appUrl || null,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Run failed");
      }
      setShowForm(false);
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

  return (
    <main className="max-w-6xl mx-auto p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">LLM Test Lab</h1>
          <p className="text-gray-400 mt-1">Evaluation runs</p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/trends" className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
            📈 Trends
          </Link>
          <Link href="/compare" className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
            ⚖ Compare
          </Link>
          <button onClick={() => setShowForm(true)} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
            + New Run
          </button>
          <button onClick={() => { clearToken(); router.push("/login"); }} className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
            Sign Out
          </button>
        </div>
      </div>

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
                <label className="block text-sm text-gray-400 mb-1">Scenarios file path</label>
                <input type="text" value={scenariosPath} onChange={(e) => setScenariosPath(e.target.value)}
                  placeholder="/path/to/scenarios.yaml"
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500 font-mono" required />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">App endpoint URL <span className="text-gray-600">(optional)</span></label>
                <input type="text" value={appUrl} onChange={(e) => setAppUrl(e.target.value)}
                  placeholder="https://your-app.com/ask"
                  className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500 font-mono" />
                <p className="text-xs text-gray-500 mt-1">POST {`{ question }`} → expects {`{ answer }`} back. Leave blank for echo mode.</p>
              </div>
              {formError && <p className="text-red-400 text-sm">{formError}</p>}
              <div className="flex gap-3 pt-2">
                <button type="submit" disabled={submitting}
                  className="flex-1 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed text-white py-2 rounded-lg text-sm font-medium transition-colors">
                  {submitting ? "Running eval..." : "Run Evaluation"}
                </button>
                <button type="button" onClick={() => { setShowForm(false); setFormError(null); }}
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
        <p className="text-gray-500">No runs yet. Click "+ New Run" to create one.</p>
      ) : (
        <table className="w-full text-sm text-left border border-gray-700 rounded-lg overflow-hidden">
          <thead className="bg-gray-800 text-gray-300">
            <tr>
              <th className="px-4 py-3">Run ID</th>
              <th className="px-4 py-3">Project</th>
              <th className="px-4 py-3">Variant</th>
              <th className="px-4 py-3">Scenarios</th>
              <th className="px-4 py-3">Avg Score</th>
              <th className="px-4 py-3">Created</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run, i) => {
              const avg = run.results.length > 0
                ? (run.results.reduce((s, r) => s + r.score, 0) / run.results.length).toFixed(2)
                : "—";
              return (
                <tr key={run.run_id} className={i % 2 === 0 ? "bg-gray-900" : "bg-gray-950"}>
                  <td className="px-4 py-3 font-mono text-xs text-gray-400">{run.run_id.slice(0, 8)}...</td>
                  <td className="px-4 py-3 text-white">{run.project}</td>
                  <td className="px-4 py-3 text-gray-300">{run.variant_name}</td>
                  <td className="px-4 py-3 text-gray-300">{run.results.length}</td>
                  <td className="px-4 py-3">
                    <span className={`font-bold ${parseFloat(avg) >= 0.8 ? "text-green-400" : parseFloat(avg) >= 0.5 ? "text-yellow-400" : "text-red-400"}`}>
                      {avg}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {run.created_at ? new Date(run.created_at).toLocaleString() : "—"}
                  </td>
                  <td className="px-4 py-3 flex items-center gap-3">
                    <Link href={`/runs/${run.run_id}`} className="text-blue-400 hover:underline">View →</Link>
                    <button onClick={() => handleDelete(run.run_id)} className="text-red-500 hover:text-red-400 text-xs transition-colors">🗑 Delete</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </main>
  );
}

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchRuns, Run } from "@/lib/api";

export default function HomePage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRuns()
      .then(setRuns)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <main className="max-w-5xl mx-auto p-8">
      <h1 className="text-3xl font-bold text-white mb-2">LLM Test Lab</h1>
      <p className="text-gray-400">Loading runs...</p>
    </main>
  );

  if (error) return (
    <main className="max-w-5xl mx-auto p-8">
      <h1 className="text-3xl font-bold text-white mb-2">LLM Test Lab</h1>
      <p className="text-red-400">Failed to connect: {error}</p>
      <p className="text-gray-400 text-sm mt-1">Make sure FastAPI is running on http://127.0.0.1:8000</p>
    </main>
  );

  return (
    <main className="max-w-5xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-2 text-white">LLM Test Lab</h1>
      <p className="text-gray-400 mb-8">Evaluation runs</p>

      {runs.length === 0 ? (
        <p className="text-gray-500">No runs yet. POST to /api/run-local to create one.</p>
      ) : (
        <table className="w-full text-sm text-left border border-gray-700 rounded-lg overflow-hidden">
          <thead className="bg-gray-800 text-gray-300">
            <tr>
              <th className="px-4 py-3">Run ID</th>
              <th className="px-4 py-3">Project</th>
              <th className="px-4 py-3">Variant</th>
              <th className="px-4 py-3">Scenarios</th>
              <th className="px-4 py-3">Avg Score</th>
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
                  <td className="px-4 py-3">
                    <Link href={`/runs/${run.run_id}`} className="text-blue-400 hover:underline">
                      View →
                    </Link>
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

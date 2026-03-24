"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { use } from "react";
import { fetchRun, Run } from "@/lib/api";

export default function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRun(id)
      .then(setRun)
      .catch((e) => setError(String(e)));
  }, [id]);

  if (error) return (
    <main className="max-w-5xl mx-auto p-8">
      <p className="text-red-400">{error}</p>
      <Link href="/" className="text-blue-400 hover:underline text-sm">← Back</Link>
    </main>
  );

  if (!run) return (
    <main className="max-w-5xl mx-auto p-8">
      <p className="text-gray-400">Loading...</p>
    </main>
  );

  const avg = run.results.length > 0
    ? (run.results.reduce((s, r) => s + r.score, 0) / run.results.length).toFixed(2)
    : "—";

  return (
    <main className="max-w-5xl mx-auto p-8">
      <Link href="/" className="text-blue-400 hover:underline text-sm">← Back to runs</Link>
      <h1 className="text-2xl font-bold text-white mt-4 mb-1">Run: {run.run_id.slice(0, 8)}...</h1>
      <p className="text-gray-400 mb-6">
        Project: <span className="text-white">{run.project}</span> · Variant:{" "}
        <span className="text-white">{run.variant_name}</span> · Avg Score:{" "}
        <span className="text-green-400 font-bold">{avg}</span>
      </p>

      <table className="w-full text-sm text-left border border-gray-700 rounded-lg overflow-hidden">
        <thead className="bg-gray-800 text-gray-300">
          <tr>
            <th className="px-4 py-3">Scenario</th>
            <th className="px-4 py-3">Score</th>
            <th className="px-4 py-3">Latency (ms)</th>
            <th className="px-4 py-3">Judge</th>
            <th className="px-4 py-3">Reason</th>
          </tr>
        </thead>
        <tbody>
          {run.results.map((r, i) => (
            <tr key={r.scenario_id} className={i % 2 === 0 ? "bg-gray-900" : "bg-gray-950"}>
              <td className="px-4 py-3 font-mono text-xs text-gray-300">{r.scenario_id}</td>
              <td className="px-4 py-3">
                <span className={`font-bold ${r.score >= 0.8 ? "text-green-400" : r.score >= 0.5 ? "text-yellow-400" : "text-red-400"}`}>
                  {r.score.toFixed(2)}
                </span>
              </td>
              <td className="px-4 py-3 text-gray-400">{r.latency_ms.toFixed(2)}</td>
              <td className="px-4 py-3 text-gray-400 font-mono text-xs">{r.judge_model}</td>
              <td className="px-4 py-3 text-gray-300 text-xs max-w-xs">{r.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}

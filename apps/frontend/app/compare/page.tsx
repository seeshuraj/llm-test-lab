"use client";

import { useEffect, useState } from "react";
import { fetchRuns, fetchRun, Run } from "@/lib/api";
import Link from "next/link";

export default function ComparePage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [runAId, setRunAId] = useState("");
  const [runBId, setRunBId] = useState("");
  const [runA, setRunA] = useState<Run | null>(null);
  const [runB, setRunB] = useState<Run | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchRuns().then(setRuns).catch(console.error);
  }, []);

  const handleCompare = async () => {
    if (!runAId || !runBId) return;
    setLoading(true);
    try {
      const [a, b] = await Promise.all([fetchRun(runAId), fetchRun(runBId)]);
      setRunA(a);
      setRunB(b);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  // Build scenario-keyed map for both runs
  const allScenarioIds = Array.from(
    new Set([
      ...(runA?.results.map((r) => r.scenario_id) ?? []),
      ...(runB?.results.map((r) => r.scenario_id) ?? []),
    ])
  );

  const mapA = Object.fromEntries(runA?.results.map((r) => [r.scenario_id, r]) ?? []);
  const mapB = Object.fromEntries(runB?.results.map((r) => [r.scenario_id, r]) ?? []);

  const avgA = runA && runA.results.length > 0
    ? runA.results.reduce((s, r) => s + r.score, 0) / runA.results.length
    : null;
  const avgB = runB && runB.results.length > 0
    ? runB.results.reduce((s, r) => s + r.score, 0) / runB.results.length
    : null;

  const scoreBadge = (score: number | undefined) => {
    if (score === undefined) return <span className="text-gray-500">—</span>;
    const color = score >= 0.8 ? "text-green-400" : score >= 0.5 ? "text-yellow-400" : "text-red-400";
    return <span className={`font-bold ${color}`}>{score.toFixed(2)}</span>;
  };

  const diffBadge = (a: number | undefined, b: number | undefined) => {
    if (a === undefined || b === undefined) return <span className="text-gray-500">—</span>;
    const diff = b - a;
    if (Math.abs(diff) < 0.01) return <span className="text-gray-400">±0.00</span>;
    return diff > 0
      ? <span className="text-green-400 font-bold">▲ +{diff.toFixed(2)}</span>
      : <span className="text-red-400 font-bold">▼ {diff.toFixed(2)}</span>;
  };

  return (
    <main className="max-w-6xl mx-auto p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Compare Runs</h1>
          <p className="text-gray-400 mt-1">Diff two evaluation runs side by side</p>
        </div>
        <Link href="/" className="text-blue-400 hover:underline text-sm">← Back to runs</Link>
      </div>

      {/* Run selectors */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-sm text-gray-400 mb-1">Run A (baseline)</label>
          <select
            value={runAId}
            onChange={(e) => setRunAId(e.target.value)}
            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
          >
            <option value="">Select a run...</option>
            {runs.map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {r.project} / {r.variant_name} — {r.created_at ? new Date(r.created_at).toLocaleString() : r.run_id.slice(0, 8)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-1">Run B (new)</label>
          <select
            value={runBId}
            onChange={(e) => setRunBId(e.target.value)}
            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
          >
            <option value="">Select a run...</option>
            {runs.map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {r.project} / {r.variant_name} — {r.created_at ? new Date(r.created_at).toLocaleString() : r.run_id.slice(0, 8)}
              </option>
            ))}
          </select>
        </div>
      </div>

      <button
        onClick={handleCompare}
        disabled={!runAId || !runBId || loading}
        className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg text-sm font-medium transition-colors mb-8"
      >
        {loading ? "Loading..." : "Compare →"}
      </button>

      {/* Summary cards */}
      {runA && runB && (
        <>
          <div className="grid grid-cols-3 gap-4 mb-8">
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <p className="text-xs text-gray-400 mb-1">Run A — {runA.project} / {runA.variant_name}</p>
              <p className="text-2xl font-bold text-white">{avgA?.toFixed(2)}</p>
              <p className="text-xs text-gray-500">avg score</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 flex flex-col items-center justify-center">
              <p className="text-xs text-gray-400 mb-1">Delta</p>
              <p className="text-2xl font-bold">
                {avgA !== null && avgB !== null
                  ? diffBadge(avgA, avgB)
                  : "—"}
              </p>
              <p className="text-xs text-gray-500">B vs A</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <p className="text-xs text-gray-400 mb-1">Run B — {runB.project} / {runB.variant_name}</p>
              <p className="text-2xl font-bold text-white">{avgB?.toFixed(2)}</p>
              <p className="text-xs text-gray-500">avg score</p>
            </div>
          </div>

          {/* Per-scenario diff table */}
          <table className="w-full text-sm text-left border border-gray-700 rounded-lg overflow-hidden">
            <thead className="bg-gray-800 text-gray-300">
              <tr>
                <th className="px-4 py-3">Scenario</th>
                <th className="px-4 py-3">Score A</th>
                <th className="px-4 py-3">Score B</th>
                <th className="px-4 py-3">Delta</th>
                <th className="px-4 py-3">Latency A (ms)</th>
                <th className="px-4 py-3">Latency B (ms)</th>
              </tr>
            </thead>
            <tbody>
              {allScenarioIds.map((sid, i) => {
                const a = mapA[sid];
                const b = mapB[sid];
                return (
                  <tr key={sid} className={i % 2 === 0 ? "bg-gray-900" : "bg-gray-950"}>
                    <td className="px-4 py-3 font-mono text-xs text-gray-400">{sid}</td>
                    <td className="px-4 py-3">{scoreBadge(a?.score)}</td>
                    <td className="px-4 py-3">{scoreBadge(b?.score)}</td>
                    <td className="px-4 py-3">{diffBadge(a?.score, b?.score)}</td>
                    <td className="px-4 py-3 text-gray-400">{a ? `${a.latency_ms}ms` : "—"}</td>
                    <td className="px-4 py-3 text-gray-400">{b ? `${b.latency_ms}ms` : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>

          {/* Reasons diff */}
          <div className="mt-8 grid grid-cols-2 gap-4">
            {allScenarioIds.map((sid) => {
              const a = mapA[sid];
              const b = mapB[sid];
              if (!a && !b) return null;
              return (
                <div key={sid} className="bg-gray-900 border border-gray-700 rounded-xl p-4 col-span-2">
                  <p className="text-xs font-mono text-gray-400 mb-2">{sid}</p>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Run A reason</p>
                      <p className="text-sm text-gray-300">{a?.reason ?? "—"}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Run B reason</p>
                      <p className="text-sm text-gray-300">{b?.reason ?? "—"}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </main>
  );
}

"use client";

import { useEffect, useState } from "react";
import { fetchRuns, fetchRun, exportRunCSV, Run } from "@/lib/api";
import Link from "next/link";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, Legend, RadarChart, Radar,
  PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from "recharts";

const scoreColor = (s: number) =>
  s >= 0.8 ? "#10b981" : s >= 0.5 ? "#f59e0b" : "#ef4444";

function runDisplayName(r: Run) {
  return r.run_label || `${r.project}/${r.variant_name} — ${r.run_id.slice(0, 8)}`;
}

export default function ComparePage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [runAId, setRunAId] = useState("");
  const [runBId, setRunBId] = useState("");
  const [runA, setRunA] = useState<Run | null>(null);
  const [runB, setRunB] = useState<Run | null>(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<"all" | "regressions" | "improvements">("all");

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

  const allScenarioIds = Array.from(
    new Set([
      ...(runA?.results.map((r) => r.scenario_id) ?? []),
      ...(runB?.results.map((r) => r.scenario_id) ?? []),
    ])
  );

  const mapA = Object.fromEntries(runA?.results.map((r) => [r.scenario_id, r]) ?? []);
  const mapB = Object.fromEntries(runB?.results.map((r) => [r.scenario_id, r]) ?? []);

  const avgA = runA && runA.results.length > 0
    ? runA.results.reduce((s, r) => s + r.score, 0) / runA.results.length : null;
  const avgB = runB && runB.results.length > 0
    ? runB.results.reduce((s, r) => s + r.score, 0) / runB.results.length : null;

  const passRateA = runA ? (runA.results.filter(r => r.score >= 0.8).length / runA.results.length) * 100 : null;
  const passRateB = runB ? (runB.results.filter(r => r.score >= 0.8).length / runB.results.length) * 100 : null;
  const avgLatA = runA ? runA.results.reduce((s, r) => s + r.latency_ms, 0) / runA.results.length : null;
  const avgLatB = runB ? runB.results.reduce((s, r) => s + r.latency_ms, 0) / runB.results.length : null;

  const scoreBadge = (score: number | undefined) => {
    if (score === undefined) return <span className="text-gray-500">—</span>;
    const color = score >= 0.8 ? "text-green-400" : score >= 0.5 ? "text-yellow-400" : "text-red-400";
    return <span className={`font-bold ${color}`}>{score.toFixed(2)}</span>;
  };

  const diffBadge = (a: number | undefined, b: number | undefined) => {
    if (a === undefined || b === undefined) return <span className="text-gray-500">—</span>;
    const diff = b - a;
    if (Math.abs(diff) < 0.005) return <span className="text-gray-400">±0.00</span>;
    return diff > 0
      ? <span className="text-green-400 font-bold">▲ +{diff.toFixed(2)}</span>
      : <span className="text-red-400 font-bold">▼ {diff.toFixed(2)}</span>;
  };

  // Filter rows
  const filteredIds = allScenarioIds.filter((sid) => {
    const a = mapA[sid]?.score;
    const b = mapB[sid]?.score;
    if (filter === "regressions") return a !== undefined && b !== undefined && b < a - 0.005;
    if (filter === "improvements") return a !== undefined && b !== undefined && b > a + 0.005;
    return true;
  });

  // Side-by-side bar chart data
  const barCompareData = allScenarioIds.map((sid) => ({
    id: sid,
    A: mapA[sid]?.score ?? 0,
    B: mapB[sid]?.score ?? 0,
  }));

  // Radar chart — summary dimensions
  const radarData = runA && runB ? [
    { metric: "Avg Score", A: avgA ?? 0, B: avgB ?? 0 },
    { metric: "Pass Rate", A: (passRateA ?? 0) / 100, B: (passRateB ?? 0) / 100 },
    { metric: "Speed (inv)", A: avgLatA ? Math.min(1, 1000 / avgLatA) : 0, B: avgLatB ? Math.min(1, 1000 / avgLatB) : 0 },
  ] : [];

  const regressionCount = allScenarioIds.filter(sid => {
    const a = mapA[sid]?.score; const b = mapB[sid]?.score;
    return a !== undefined && b !== undefined && b < a - 0.005;
  }).length;
  const improvementCount = allScenarioIds.filter(sid => {
    const a = mapA[sid]?.score; const b = mapB[sid]?.score;
    return a !== undefined && b !== undefined && b > a + 0.005;
  }).length;

  return (
    <main className="max-w-6xl mx-auto p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Compare Runs</h1>
          <p className="text-gray-400 mt-1">Diff two evaluation runs side by side</p>
        </div>
        <Link href="/" className="text-blue-400 hover:underline text-sm">← Back to runs</Link>
      </div>

      {/* Selectors */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-sm text-gray-400 mb-1">Run A (baseline)</label>
          <select value={runAId} onChange={(e) => setRunAId(e.target.value)}
            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500">
            <option value="">Select a run...</option>
            {runs.map((r) => (
              <option key={r.run_id} value={r.run_id}>{runDisplayName(r)}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm text-gray-400 mb-1">Run B (new)</label>
          <select value={runBId} onChange={(e) => setRunBId(e.target.value)}
            className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500">
            <option value="">Select a run...</option>
            {runs.map((r) => (
              <option key={r.run_id} value={r.run_id}>{runDisplayName(r)}</option>
            ))}
          </select>
        </div>
      </div>

      <button onClick={handleCompare} disabled={!runAId || !runBId || loading}
        className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg text-sm font-medium transition-colors mb-8">
        {loading ? "Loading..." : "Compare →"}
      </button>

      {runA && runB && (
        <>
          {/* Summary stat cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {[
              { label: "Avg Score A", value: avgA?.toFixed(3) ?? "—", color: scoreColor(avgA ?? 0) },
              { label: "Avg Score B", value: avgB?.toFixed(3) ?? "—", color: scoreColor(avgB ?? 0) },
              { label: "Pass Rate A", value: `${passRateA?.toFixed(0)}%`, color: scoreColor((passRateA ?? 0) / 100) },
              { label: "Pass Rate B", value: `${passRateB?.toFixed(0)}%`, color: scoreColor((passRateB ?? 0) / 100) },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-gray-900 border border-gray-700 rounded-xl p-4 text-center">
                <p className="text-xs text-gray-500 mb-1">{label}</p>
                <p className="text-2xl font-bold" style={{ color }}>{value}</p>
              </div>
            ))}
          </div>

          {/* Delta summary + radar */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Delta card */}
            <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-gray-300 mb-4">Overall Delta (B − A)</h2>
              <div className="flex items-center justify-around">
                <div className="text-center">
                  <p className="text-xs text-gray-500 mb-1">Score</p>
                  <p className="text-3xl font-bold">
                    {avgA !== null && avgB !== null ? diffBadge(avgA, avgB) : "—"}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-gray-500 mb-1">Regressions</p>
                  <p className="text-3xl font-bold text-red-400">{regressionCount}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-gray-500 mb-1">Improvements</p>
                  <p className="text-3xl font-bold text-green-400">{improvementCount}</p>
                </div>
              </div>
            </div>

            {/* Radar chart */}
            <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
              <h2 className="text-sm font-semibold text-gray-300 mb-2">Summary Radar</h2>
              <ResponsiveContainer width="100%" height={180}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#374151" />
                  <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: "#9ca3af" }} />
                  <PolarRadiusAxis domain={[0, 1]} tick={false} axisLine={false} />
                  <Radar name={runDisplayName(runA)} dataKey="A" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.2} />
                  <Radar name={runDisplayName(runB)} dataKey="B" stroke="#10b981" fill="#10b981" fillOpacity={0.2} />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: 11, color: "#9ca3af" }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Side-by-side score bar chart */}
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-6">
            <h2 className="text-sm font-semibold text-gray-300 mb-4">Score per Scenario (A vs B)</h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={barCompareData} margin={{ top: 0, right: 20, left: -10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="id" tick={{ fontSize: 10, fill: "#6b7280" }} angle={-30} textAnchor="end" interval={0} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: "#6b7280" }} tickFormatter={(v) => v.toFixed(1)} />
                <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 12 }} />
                <Legend iconSize={10} wrapperStyle={{ fontSize: 11, color: "#9ca3af" }} />
                <Bar dataKey="A" name={runDisplayName(runA)} fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="B" name={runDisplayName(runB)} fill="#10b981" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Filter + diff table */}
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-300">Per-Scenario Diff</h2>
            <div className="flex items-center gap-2">
              <div className="flex bg-gray-800 border border-gray-600 rounded-lg p-0.5 text-xs">
                {(["all", "regressions", "improvements"] as const).map((f) => (
                  <button key={f} onClick={() => setFilter(f)}
                    className={`px-3 py-1 rounded-md capitalize transition-colors ${
                      filter === f ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
                    }`}>{f}</button>
                ))}
              </div>
              <button onClick={() => { if (runA) exportRunCSV(runA); }} className="text-xs text-gray-400 hover:text-white transition-colors" title="Export Run A CSV">⬇️ A</button>
              <button onClick={() => { if (runB) exportRunCSV(runB); }} className="text-xs text-gray-400 hover:text-white transition-colors" title="Export Run B CSV">⬇️ B</button>
            </div>
          </div>

          <div className="overflow-x-auto rounded-xl border border-gray-700 mb-8">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-800 text-gray-300">
                <tr>
                  <th className="px-4 py-3">Scenario</th>
                  <th className="px-4 py-3">Score A</th>
                  <th className="px-4 py-3">Score B</th>
                  <th className="px-4 py-3">Delta</th>
                  <th className="px-4 py-3">Latency A</th>
                  <th className="px-4 py-3">Latency B</th>
                </tr>
              </thead>
              <tbody>
                {filteredIds.map((sid, i) => {
                  const a = mapA[sid];
                  const b = mapB[sid];
                  return (
                    <tr key={sid} className={i % 2 === 0 ? "bg-gray-900" : "bg-gray-950"}>
                      <td className="px-4 py-3 font-mono text-xs text-gray-400">{sid}</td>
                      <td className="px-4 py-3">{scoreBadge(a?.score)}</td>
                      <td className="px-4 py-3">{scoreBadge(b?.score)}</td>
                      <td className="px-4 py-3">{diffBadge(a?.score, b?.score)}</td>
                      <td className="px-4 py-3 text-gray-400 text-xs">{a ? `${a.latency_ms.toFixed(0)}ms` : "—"}</td>
                      <td className="px-4 py-3 text-gray-400 text-xs">{b ? `${b.latency_ms.toFixed(0)}ms` : "—"}</td>
                    </tr>
                  );
                })}
                {filteredIds.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-500">No scenarios match the current filter.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Reasons diff */}
          <h2 className="text-sm font-semibold text-gray-300 mb-3">Judge Reasons Side-by-Side</h2>
          <div className="space-y-3">
            {filteredIds.map((sid) => {
              const a = mapA[sid];
              const b = mapB[sid];
              if (!a && !b) return null;
              const diff = a && b ? b.score - a.score : 0;
              const rowBg = diff > 0.005 ? "border-green-800" : diff < -0.005 ? "border-red-800" : "border-gray-700";
              return (
                <div key={sid} className={`bg-gray-900 border ${rowBg} rounded-xl p-4`}>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs font-mono text-gray-400">{sid}</p>
                    <span>{diffBadge(a?.score, b?.score)}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Run A — {a?.score?.toFixed(2) ?? "—"}</p>
                      <p className="text-sm text-gray-300">{a?.reason ?? "—"}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-1">Run B — {b?.score?.toFixed(2) ?? "—"}</p>
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

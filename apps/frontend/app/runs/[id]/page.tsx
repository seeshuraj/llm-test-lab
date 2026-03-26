"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { use } from "react";
import { fetchRun, exportRunCSV, Run } from "@/lib/api";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";

const scoreColor = (s: number) =>
  s >= 0.8 ? "#10b981" : s >= 0.5 ? "#f59e0b" : "#ef4444";

const CustomBarTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 text-xs max-w-xs">
      <p className="text-white font-mono mb-1">{d.id}</p>
      <p className="text-gray-300">Score: <span className="font-bold" style={{ color: scoreColor(d.score) }}>{d.score.toFixed(2)}</span></p>
      <p className="text-gray-300">Latency: <span className="text-blue-300">{d.latency.toFixed(0)} ms</span></p>
      <p className="text-gray-400 mt-1 leading-relaxed">{d.reason}</p>
    </div>
  );
};

// Skeleton placeholder card
function SkeletonCard() {
  return <div className="h-24 bg-gray-800 rounded-xl animate-pulse" />;
}

export default function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchRun(id).then(setRun).catch((e) => setError(String(e)));
  }, [id]);

  if (error) return (
    <main className="max-w-5xl mx-auto p-8">
      <p className="text-red-400">{error}</p>
      <Link href="/" className="text-blue-400 hover:underline text-sm">← Back</Link>
    </main>
  );

  // Skeleton loading state
  if (!run) return (
    <main className="max-w-6xl mx-auto p-8">
      <div className="h-4 w-24 bg-gray-700 rounded animate-pulse mb-6" />
      <div className="h-8 w-64 bg-gray-700 rounded animate-pulse mb-2" />
      <div className="h-4 w-96 bg-gray-800 rounded animate-pulse mb-8" />
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-64 bg-gray-800 rounded-xl animate-pulse" />
        ))}
      </div>
      <div className="h-64 bg-gray-800 rounded-xl animate-pulse mb-8" />
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-10 bg-gray-800 rounded animate-pulse" />
        ))}
      </div>
    </main>
  );

  const scores = run.results.map((r) => r.score);
  const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
  const minScore = scores.length ? Math.min(...scores) : 0;
  const maxScore = scores.length ? Math.max(...scores) : 0;
  const avgLatency = run.results.length
    ? run.results.reduce((a, r) => a + r.latency_ms, 0) / run.results.length
    : 0;

  const passed = scores.filter((s) => s >= 0.8).length;
  const warned = scores.filter((s) => s >= 0.5 && s < 0.8).length;
  const failed = scores.filter((s) => s < 0.5).length;

  const barData = run.results.map((r) => ({
    id: r.scenario_id,
    score: r.score,
    latency: r.latency_ms,
    reason: r.reason,
  }));

  const donutData = [
    { name: "Pass (≥0.8)", value: passed, color: "#10b981" },
    { name: "Warn (0.5–0.8)", value: warned, color: "#f59e0b" },
    { name: "Fail (<0.5)", value: failed, color: "#ef4444" },
  ].filter((d) => d.value > 0);

  const buckets: Record<string, number> = { "0.0–0.2": 0, "0.2–0.4": 0, "0.4–0.6": 0, "0.6–0.8": 0, "0.8–1.0": 0 };
  scores.forEach((s) => {
    if (s < 0.2) buckets["0.0–0.2"]++;
    else if (s < 0.4) buckets["0.2–0.4"]++;
    else if (s < 0.6) buckets["0.4–0.6"]++;
    else if (s < 0.8) buckets["0.6–0.8"]++;
    else buckets["0.8–1.0"]++;
  });
  const distData = Object.entries(buckets).map(([range, count]) => ({ range, count }));

  const displayName = run.run_label || `${run.run_id.slice(0, 8)}…`;

  return (
    <main className="max-w-6xl mx-auto p-8">
      <Link href="/" className="text-blue-400 hover:underline text-sm">← Back to runs</Link>

      {/* Header */}
      <div className="mt-4 mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            {run.run_label
              ? <>{run.run_label} <span className="text-gray-500 font-mono text-base ml-2">{run.run_id.slice(0, 8)}</span></>
              : <>Run: <span className="font-mono text-blue-300">{run.run_id.slice(0, 8)}…</span></>
            }
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            Project: <span className="text-white">{run.project}</span> ·
            Variant: <span className="text-white">{run.variant_name}</span> ·
            Model: <span className="text-white">{run.model_name}</span> ·
            {run.created_at && <> {new Date(run.created_at).toLocaleString()}</>}
          </p>
        </div>
        <button
          onClick={() => exportRunCSV(run)}
          className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
        >
          ⬇️ Export CSV
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        {[
          { label: "Avg Score", value: avg.toFixed(3), color: scoreColor(avg) },
          { label: "Min Score", value: minScore.toFixed(3), color: scoreColor(minScore) },
          { label: "Max Score", value: maxScore.toFixed(3), color: scoreColor(maxScore) },
          { label: "Avg Latency", value: `${avgLatency.toFixed(0)} ms`, color: "#60a5fa" },
        ].map((c) => (
          <div key={c.label} className="bg-gray-900 border border-gray-700 rounded-xl p-4 text-center">
            <p className="text-xs text-gray-500 mb-1">{c.label}</p>
            <p className="text-2xl font-bold" style={{ color: c.color }}>{c.value}</p>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Pass / Warn / Fail</h2>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={donutData} cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                dataKey="value" paddingAngle={3}>
                {donutData.map((d, i) => <Cell key={i} fill={d.color} />)}
              </Pie>
              <Tooltip formatter={(v: any, name: any) => [v, name]} contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 12 }} />
              <Legend iconSize={10} wrapperStyle={{ fontSize: 12, color: "#9ca3af" }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex justify-around mt-2 text-center">
            <div><p className="text-xs text-gray-500">Pass</p><p className="text-green-400 font-bold">{passed}</p></div>
            <div><p className="text-xs text-gray-500">Warn</p><p className="text-yellow-400 font-bold">{warned}</p></div>
            <div><p className="text-xs text-gray-500">Fail</p><p className="text-red-400 font-bold">{failed}</p></div>
          </div>
        </div>

        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Score Distribution</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={distData} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="range" tick={{ fontSize: 9, fill: "#6b7280" }} />
              <YAxis tick={{ fontSize: 10, fill: "#6b7280" }} allowDecimals={false} />
              <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {distData.map((d, i) => {
                  const midpoint = parseFloat(d.range.split("–")[0]) + 0.1;
                  return <Cell key={i} fill={scoreColor(midpoint)} />;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-gray-900 border border-gray-700 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Latency per Scenario (ms)</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={barData} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="id" tick={{ fontSize: 9, fill: "#6b7280" }} />
              <YAxis tick={{ fontSize: 10, fill: "#6b7280" }} />
              <Tooltip contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 12 }}
                formatter={(v: any) => [`${Number(v).toFixed(0)} ms`, "Latency"]} />
              <Bar dataKey="latency" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Per-scenario score bar chart */}
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-8">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Score per Scenario</h2>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={barData} margin={{ top: 0, right: 20, left: -10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="id" tick={{ fontSize: 10, fill: "#6b7280" }} angle={-30} textAnchor="end" interval={0} />
            <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: "#6b7280" }} tickFormatter={(v) => v.toFixed(1)} />
            <Tooltip content={<CustomBarTooltip />} />
            <Bar dataKey="score" radius={[4, 4, 0, 0]}>
              {barData.map((d, i) => <Cell key={i} fill={scoreColor(d.score)} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Results table */}
      <h2 className="text-sm font-semibold text-gray-300 mb-3">Scenario Details</h2>
      <div className="overflow-x-auto rounded-xl border border-gray-700">
        <table className="w-full text-sm text-left">
          <thead className="bg-gray-800 text-gray-300">
            <tr>
              <th className="px-4 py-3">Scenario</th>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3">Latency</th>
              <th className="px-4 py-3">Judge</th>
              <th className="px-4 py-3">Reason</th>
            </tr>
          </thead>
          <tbody>
            {run.results.map((r, i) => (
              <tr key={r.scenario_id} className={i % 2 === 0 ? "bg-gray-900" : "bg-gray-950"}>
                <td className="px-4 py-3 font-mono text-xs text-gray-300">{r.scenario_id}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-2 bg-gray-700 rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${r.score * 100}%`, backgroundColor: scoreColor(r.score) }} />
                    </div>
                    <span className="font-bold text-xs" style={{ color: scoreColor(r.score) }}>{r.score.toFixed(2)}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-blue-300 text-xs">{r.latency_ms.toFixed(0)} ms</td>
                <td className="px-4 py-3 text-gray-400 font-mono text-xs">{r.judge_model}</td>
                <td className="px-4 py-3 text-gray-300 text-xs leading-relaxed max-w-sm">{r.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}

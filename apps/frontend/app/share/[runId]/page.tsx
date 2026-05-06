"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchSharedRun, Run } from "@/lib/api";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell,
} from "recharts";

// ── Safe number helpers ───────────────────────────────────────────────
const safeFixed = (v: number | null | undefined, decimals = 2): string =>
  v == null || isNaN(v) ? "—" : v.toFixed(decimals);

const safeScore = (v: number | null | undefined): number =>
  v == null || isNaN(v) ? 0 : v;

const scoreColor = (s: number | null | undefined) => {
  const n = safeScore(s);
  return n >= 0.8 ? "#10b981" : n >= 0.5 ? "#f59e0b" : "#ef4444";
};

export default function SharePage() {
  const params = useParams();
  const runId = params.runId as string;
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    fetchSharedRun(runId)
      .then(setRun)
      .catch((e) => setError(String(e)));
  }, [runId]);

  if (error) return (
    <main className="max-w-3xl mx-auto p-8 text-center">
      <p className="text-red-400 text-lg mb-2">Run not found</p>
      <p className="text-gray-500 text-sm">{error}</p>
      <p className="text-gray-600 text-xs mt-3">The run ID may be invalid, or this run has not been shared publicly.</p>
    </main>
  );

  if (!run) return (
    <main className="max-w-3xl mx-auto p-8">
      <div className="space-y-3 animate-pulse">
        <div className="h-4 w-32 bg-gray-800 rounded" />
        <div className="h-8 w-64 bg-gray-800 rounded" />
        <div className="h-4 w-96 bg-gray-800 rounded" />
        <div className="grid grid-cols-4 gap-4 mt-6">
          {[...Array(4)].map((_, i) => <div key={i} className="h-20 bg-gray-800 rounded-xl" />)}
        </div>
        <div className="h-52 bg-gray-800 rounded-xl mt-4" />
      </div>
    </main>
  );

  const results = run.results ?? [];
  const hasNoResults = results.length === 0;

  const scores = results.map((r) => safeScore(r.score));
  const avgLatency = results.length
    ? results.reduce((a, r) => a + safeScore(r.latency_ms), 0) / results.length
    : 0;
  const passCount = scores.filter((s) => s >= 0.8).length;
  const warnCount = scores.filter((s) => s >= 0.5 && s < 0.8).length;
  const failCount = scores.filter((s) => s < 0.5).length;

  const barData = results.map((r) => ({
    name: r.scenario_id,
    score: safeScore(r.score),
  }));

  return (
    <main className="max-w-4xl mx-auto p-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs bg-blue-900 text-blue-300 px-2 py-0.5 rounded-full font-medium">📊 Shared Eval Report</span>
          </div>
          <h1 className="text-3xl font-bold text-white">{run.project}</h1>
          <p className="text-gray-400 mt-1">
            Variant: <span className="text-gray-200">{run.variant_name}</span>
            {" · "}
            Model: <span className="text-gray-200">{run.model_name}</span>
            {" · "}
            {run.created_at && new Date(run.created_at).toLocaleString()}
          </p>
        </div>
        <Link
          href="/"
          className="text-xs bg-gray-700 hover:bg-gray-600 text-white px-3 py-1.5 rounded-lg transition-colors"
        >
          Try LLM Test Lab →
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Avg Score</p>
          <p className="text-3xl font-bold" style={{ color: scoreColor(run.avg_score) }}>
            {safeFixed(run.avg_score)}
          </p>
        </div>
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Avg Latency</p>
          <p className="text-3xl font-bold text-white">
            {safeFixed(avgLatency, 0)}<span className="text-sm text-gray-400 ml-1">ms</span>
          </p>
        </div>
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Pass / Warn / Fail</p>
          <p className="text-lg font-bold">
            <span className="text-green-400">{passCount}</span>
            <span className="text-gray-500"> / </span>
            <span className="text-yellow-400">{warnCount}</span>
            <span className="text-gray-500"> / </span>
            <span className="text-red-400">{failCount}</span>
          </p>
        </div>
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Scenarios</p>
          <p className="text-3xl font-bold text-white">{results.length}</p>
        </div>
      </div>

      {/* No results banner */}
      {hasNoResults && (
        <div className="bg-yellow-950 border border-yellow-700 rounded-xl p-5 mb-8 text-center">
          <p className="text-yellow-300 font-semibold text-sm">⚠️ No scenario results in this run</p>
          <p className="text-yellow-500 text-xs mt-1">The run completed but returned no scored scenarios. The app endpoint may have been unreachable.</p>
        </div>
      )}

      {/* Score bar chart — only when results exist */}
      {!hasNoResults && (
        <>
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-5 mb-8">
            <h2 className="text-sm font-semibold text-gray-300 mb-3">Score per Scenario</h2>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={barData} margin={{ top: 5, right: 20, left: -30, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#6b7280" }} angle={-30} textAnchor="end" interval={0} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: "#6b7280" }} tickFormatter={(v) => safeFixed(v, 1)} />
                <Tooltip
                  contentStyle={{ background: "#111827", border: "1px solid #374151", borderRadius: 8, fontSize: 12 }}
                  formatter={(v: any) => [safeFixed(Number(v), 3), "Score"]}
                />
                <ReferenceLine y={0.8} stroke="#ef4444" strokeDasharray="4 4" label={{ value: "threshold", fill: "#ef4444", fontSize: 10 }} />
                <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                  {barData.map((d, i) => (
                    <Cell key={i} fill={scoreColor(d.score)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Scenario table */}
          <div className="overflow-x-auto rounded-xl border border-gray-700">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-800 text-gray-300">
                <tr>
                  <th className="px-4 py-3">Scenario</th>
                  <th className="px-4 py-3">Score</th>
                  <th className="px-4 py-3">Latency</th>
                  <th className="px-4 py-3">Judge Reason</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r, i) => (
                  <tr key={r.scenario_id} className={i % 2 === 0 ? "bg-gray-900" : "bg-gray-950"}>
                    <td className="px-4 py-3 font-mono text-xs text-gray-300">{r.scenario_id}</td>
                    <td className="px-4 py-3">
                      <span className="font-bold text-sm" style={{ color: scoreColor(r.score) }}>
                        {safeFixed(r.score)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{safeFixed(r.latency_ms, 0)}ms</td>
                    <td className="px-4 py-3 text-gray-400 text-xs max-w-xs">{r.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Footer CTA */}
      <div className="mt-8 text-center">
        <p className="text-gray-500 text-sm mb-3">Want to run your own LLM evaluations?</p>
        <Link
          href="/"
          className="inline-block bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          Try LLM Test Lab Free →
        </Link>
      </div>
    </main>
  );
}

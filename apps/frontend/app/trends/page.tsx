"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fetchRuns, Run } from "@/lib/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

const COLORS = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
  "#8b5cf6", "#06b6d4", "#ec4899", "#84cc16",
];

export default function TrendsPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [threshold, setThreshold] = useState(0.8);

  useEffect(() => {
    fetchRuns()
      .then(setRuns)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  // Group runs by project
  const projects = Array.from(new Set(runs.map((r) => r.project)));

  // Build chart data: one point per run, x = created_at, y = avg score
  const chartDataByProject: Record<string, { time: string; score: number; run_id: string }[]> = {};
  for (const project of projects) {
    chartDataByProject[project] = runs
      .filter((r) => r.project === project)
      .sort((a, b) => (a.created_at ?? "").localeCompare(b.created_at ?? ""))
      .map((r) => ({
        time: r.created_at ? new Date(r.created_at).toLocaleTimeString() : r.run_id.slice(0, 8),
        score: r.results.length > 0
          ? parseFloat((r.results.reduce((s, x) => s + x.score, 0) / r.results.length).toFixed(4))
          : 0,
        run_id: r.run_id.slice(0, 8),
      }));
  }

  // Merge all points into a unified timeline for multi-line chart
  const allTimes = Array.from(
    new Set(runs
      .sort((a, b) => (a.created_at ?? "").localeCompare(b.created_at ?? ""))
      .map((r) => r.created_at ? new Date(r.created_at).toLocaleTimeString() : r.run_id.slice(0, 8))
    )
  );

  const chartData = allTimes.map((time) => {
    const point: Record<string, string | number> = { time };
    for (const project of projects) {
      const match = chartDataByProject[project].find((p) => p.time === time);
      if (match) point[project] = match.score;
    }
    return point;
  });

  // Stats per project
  const stats = projects.map((project) => {
    const points = chartDataByProject[project];
    const scores = points.map((p) => p.score);
    const latest = scores[scores.length - 1] ?? 0;
    const first = scores[0] ?? 0;
    const trend = latest - first;
    const avg = scores.reduce((a, b) => a + b, 0) / (scores.length || 1);
    return { project, latest, trend, avg, runs: scores.length };
  });

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 text-sm">
        <p className="text-gray-400 mb-1">{label}</p>
        {payload.map((p: any) => (
          <p key={p.name} style={{ color: p.color }} className="font-mono">
            {p.name}: {p.value?.toFixed(2)}
          </p>
        ))}
      </div>
    );
  };

  return (
    <main className="max-w-6xl mx-auto p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Score Trends</h1>
          <p className="text-gray-400 mt-1">Avg score over time per project</p>
        </div>
        <Link href="/" className="text-blue-400 hover:underline text-sm">← Back to runs</Link>
      </div>

      {loading ? (
        <p className="text-gray-400">Loading...</p>
      ) : runs.length < 2 ? (
        <p className="text-gray-500">Run at least 2 evaluations to see trends.</p>
      ) : (
        <>
          {/* Threshold control */}
          <div className="flex items-center gap-4 mb-6">
            <label className="text-sm text-gray-400">Quality threshold:</label>
            <input
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={threshold}
              onChange={(e) => setThreshold(parseFloat(e.target.value))}
              className="bg-gray-800 border border-gray-600 rounded-lg px-3 py-1 text-white text-sm w-24 focus:outline-none focus:border-blue-500"
            />
            <span className="text-xs text-gray-500">Red line = minimum acceptable score</span>
          </div>

          {/* Chart */}
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 mb-8">
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="time" stroke="#6b7280" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 1]} stroke="#6b7280" tick={{ fontSize: 11 }} tickFormatter={(v) => v.toFixed(1)} />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ color: "#9ca3af", fontSize: 12 }} />
                <ReferenceLine
                  y={threshold}
                  stroke="#ef4444"
                  strokeDasharray="6 3"
                  label={{ value: `threshold ${threshold}`, fill: "#ef4444", fontSize: 11 }}
                />
                {projects.map((project, i) => (
                  <Line
                    key={project}
                    type="monotone"
                    dataKey={project}
                    stroke={COLORS[i % COLORS.length]}
                    strokeWidth={2}
                    dot={{ r: 4, fill: COLORS[i % COLORS.length] }}
                    activeDot={{ r: 6 }}
                    connectNulls
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Stats cards per project */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {stats.map((s, i) => (
              <div key={s.project} className="bg-gray-900 border border-gray-700 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                  <p className="text-white font-medium text-sm">{s.project}</p>
                </div>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div>
                    <p className="text-xs text-gray-500">Latest</p>
                    <p className={`font-bold text-lg ${s.latest >= threshold ? "text-green-400" : "text-red-400"}`}>
                      {s.latest.toFixed(2)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Trend</p>
                    <p className={`font-bold text-lg ${s.trend >= 0 ? "text-green-400" : "text-red-400"}`}>
                      {s.trend >= 0 ? "▲" : "▼"} {Math.abs(s.trend).toFixed(2)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Runs</p>
                    <p className="font-bold text-lg text-white">{s.runs}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </main>
  );
}

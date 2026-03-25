"use client";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

type EvalRun = {
  id: string;
  created_at: string;
  prompt: string;
  model: string;
  score: number;
  latency: number;
};

export default function DashboardPage() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchRuns() {
      const { data } = await supabase
        .from("eval_runs")
        .select("id, created_at, prompt, model, score, latency")
        .order("created_at", { ascending: false })
        .limit(50);
      setRuns(data ?? []);
      setLoading(false);
    }
    fetchRuns();
  }, []);

  return (
    <main className="min-h-screen bg-gray-950 text-white p-8 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold">📊 Eval History</h1>
          <p className="text-gray-400 mt-1">All past evaluation runs</p>
        </div>
        <a
          href="/eval"
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2 rounded-lg text-sm font-medium transition"
        >
          + New Eval
        </a>
      </div>

      {loading ? (
        <p className="text-gray-400">Loading...</p>
      ) : runs.length === 0 ? (
        <p className="text-gray-400">No eval runs yet. <a href="/eval" className="text-indigo-400 underline">Run your first eval →</a></p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 border-b border-gray-800 text-left">
                <th className="pb-3 pr-4">Time</th>
                <th className="pb-3 pr-4">Prompt</th>
                <th className="pb-3 pr-4">Model</th>
                <th className="pb-3 pr-4">Score</th>
                <th className="pb-3">Latency</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id} className="border-b border-gray-800 hover:bg-gray-900">
                  <td className="py-3 pr-4 text-gray-400 whitespace-nowrap">
                    {new Date(r.created_at).toLocaleString()}
                  </td>
                  <td className="py-3 pr-4 text-gray-200 max-w-xs truncate">
                    {r.prompt}
                  </td>
                  <td className="py-3 pr-4">
                    <span className="bg-indigo-900 text-indigo-300 text-xs px-2 py-1 rounded-full">
                      {r.model}
                    </span>
                  </td>
                  <td className="py-3 pr-4">
                    <span className={`font-bold ${r.score >= 70 ? "text-green-400" : r.score >= 40 ? "text-yellow-400" : "text-red-400"}`}>
                      {r.score}%
                    </span>
                  </td>
                  <td className="py-3 text-gray-400">{r.latency}ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}

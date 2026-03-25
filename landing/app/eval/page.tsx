"use client";
import { useState } from "react";

type Result = { model: string; output: string; latency: number; score: number };

export default function EvalPage() {
  const [prompt, setPrompt] = useState("");
  const [expected, setExpected] = useState("");
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    const res = await fetch("/api/eval", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, expected }),
    });
    const data = await res.json();
    setResults(data.results);
    setLoading(false);
  };

  return (
    <main className="min-h-screen bg-gray-950 text-white p-8 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold mb-2">🧪 LLM Eval Engine</h1>
      <p className="text-gray-400 mb-8">Run your prompt across models and compare scores.</p>

      <div className="flex flex-col gap-4 mb-6">
        <textarea
          rows={4}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Enter your prompt..."
          className="bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white resize-none focus:outline-none focus:border-indigo-500"
        />
        <textarea
          rows={3}
          value={expected}
          onChange={(e) => setExpected(e.target.value)}
          placeholder="Expected output (used for scoring)..."
          className="bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white resize-none focus:outline-none focus:border-indigo-500"
        />
        <button
          onClick={run}
          disabled={loading || !prompt || !expected}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-900 text-white py-3 rounded-lg font-semibold transition"
        >
          {loading ? "Running evals..." : "▶ Run Eval"}
        </button>
      </div>

      {results.length > 0 && (
        <div className="grid gap-4">
          {results.map((r) => (
            <div key={r.model} className="bg-gray-900 border border-gray-700 rounded-xl p-5">
              <div className="flex justify-between items-center mb-3">
                <span className="font-semibold text-indigo-400">{r.model}</span>
                <div className="flex gap-4 text-sm text-gray-400">
                  <span>⏱ {r.latency}ms</span>
                  <span className={`font-bold ${r.score >= 70 ? "text-green-400" : r.score >= 40 ? "text-yellow-400" : "text-red-400"}`}>
                    Score: {r.score}%
                  </span>
                </div>
              </div>
              <p className="text-gray-300 text-sm whitespace-pre-wrap">{r.output}</p>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}

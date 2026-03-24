"use client";

import { useState } from "react";

export default function WaitlistFormClient() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("loading");
    try {
      const res = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!res.ok) throw new Error();
      setStatus("done");
    } catch {
      setStatus("error");
    }
  };

  if (status === "done") {
    return (
      <div className="bg-green-950 border border-green-700 rounded-xl p-6">
        <p className="text-green-400 font-medium text-lg">🎉 You're on the list!</p>
        <p className="text-gray-400 text-sm mt-1">We'll reach out as soon as early access opens.</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-3 max-w-md mx-auto">
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@company.com"
        required
        className="flex-1 bg-gray-900 border border-gray-600 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500"
      />
      <button
        type="submit"
        disabled={status === "loading"}
        className="bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white px-5 py-3 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
      >
        {status === "loading" ? "..." : "Join Waitlist"}
      </button>
      {status === "error" && (
        <p className="text-red-400 text-xs mt-2 absolute">Something went wrong. Try again.</p>
      )}
    </form>
  );
}

"use client";

import { useState } from "react";

export default function WaitlistFormClient() {
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setStatus("loading");
    const data = new FormData(e.currentTarget);
    try {
      const res = await fetch("https://formspree.io/f/xwvwekgw", {
        method: "POST",
        body: data,
        headers: { Accept: "application/json" },
      });
      if (res.ok) setStatus("done");
      else setStatus("error");
    } catch {
      setStatus("error");
    }
  };

  if (status === "done") {
    return (
      <div className="bg-green-950 border border-green-700 rounded-xl p-6 max-w-md mx-auto">
        <p className="text-green-400 font-medium text-lg">🎉 You're on the list!</p>
        <p className="text-gray-400 text-sm mt-1">We'll reach out as soon as early access opens.</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 max-w-md mx-auto">
      <input
        type="email"
        name="email"
        required
        placeholder="you@company.com"
        className="flex-1 bg-gray-900 border border-gray-600 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500"
      />
      <textarea
        name="message"
        rows={3}
        placeholder="What are you building? (optional)"
        className="bg-gray-900 border border-gray-600 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500 resize-none"
      />
      <button
        type="submit"
        disabled={status === "loading"}
        className="bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white px-5 py-3 rounded-lg text-sm font-medium transition-colors"
      >
        {status === "loading" ? "Submitting..." : "Join Waitlist"}
      </button>
      {status === "error" && (
        <p className="text-red-400 text-xs mt-2">Something went wrong. Try again.</p>
      )}
    </form>
  );
}

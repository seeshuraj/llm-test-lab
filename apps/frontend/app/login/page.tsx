"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login, register, setToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register" | "forgot">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [forgotSent, setForgotSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const token = mode === "login"
        ? await login(email, password)
        : await register(email, password);
      setToken(token);
      router.push("/");
    } catch (e) {
      setError(String(e).replace("Error: ", ""));
    } finally {
      setLoading(false);
    }
  };

  const handleForgot = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    // Placeholder: in production connect to /api/auth/forgot-password
    // For now, show a friendly confirmation regardless
    await new Promise((r) => setTimeout(r, 800));
    setForgotSent(true);
    setLoading(false);
  };

  return (
    <main className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">LLM Test Lab</h1>
          <p className="text-gray-400 mt-1 text-sm">Evaluate your AI apps with confidence</p>
        </div>

        <div className="bg-gray-900 border border-gray-700 rounded-xl p-6">
          {mode !== "forgot" ? (
            <>
              {/* Tab toggle */}
              <div className="flex bg-gray-800 rounded-lg p-1 mb-6">
                <button onClick={() => setMode("login")}
                  className={`flex-1 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    mode === "login" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
                  }`}>Sign In</button>
                <button onClick={() => setMode("register")}
                  className={`flex-1 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    mode === "register" ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
                  }`}>Register</button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Email</label>
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                    placeholder="you@example.com" required />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Password</label>
                  <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                    placeholder="••••••••" required />
                </div>

                {error && <p className="text-red-400 text-sm">{error}</p>}

                <button type="submit" disabled={loading}
                  className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed text-white py-2 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2">
                  {loading && (
                    <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                  )}
                  {loading ? "Please wait..." : mode === "login" ? "Sign In" : "Create Account"}
                </button>
              </form>

              {mode === "login" && (
                <p className="text-center mt-4">
                  <button onClick={() => { setMode("forgot"); setError(null); setForgotSent(false); }}
                    className="text-xs text-gray-500 hover:text-gray-300 transition-colors">
                    Forgot password?
                  </button>
                </p>
              )}
            </>
          ) : (
            <>
              <button onClick={() => setMode("login")} className="text-xs text-gray-500 hover:text-gray-300 mb-4 flex items-center gap-1">
                ← Back to sign in
              </button>
              <h2 className="text-white font-semibold mb-1">Reset password</h2>
              <p className="text-gray-400 text-xs mb-4">Enter your email and we'll send reset instructions.</p>

              {forgotSent ? (
                <div className="bg-green-900/40 border border-green-700 rounded-lg px-4 py-3 text-green-300 text-sm">
                  ✅ If that email exists, a reset link has been sent.
                </div>
              ) : (
                <form onSubmit={handleForgot} className="space-y-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Email</label>
                    <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
                      placeholder="you@example.com" required />
                  </div>
                  {error && <p className="text-red-400 text-sm">{error}</p>}
                  <button type="submit" disabled={loading}
                    className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-white py-2 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2">
                    {loading && (
                      <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                      </svg>
                    )}
                    {loading ? "Sending..." : "Send reset link"}
                  </button>
                </form>
              )}
            </>
          )}
        </div>
      </div>
    </main>
  );
}

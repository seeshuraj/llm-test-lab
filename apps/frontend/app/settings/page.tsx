"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { authHeaders } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

interface BillingStatus {
  is_pro: boolean;
  email: string;
  stripe_customer_id: string | null;
}

// Inner component that uses useSearchParams — must be inside <Suspense>
function SettingsContent() {
  const searchParams = useSearchParams();
  const upgraded = searchParams.get("upgraded");

  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchBillingStatus();
  }, []);

  async function fetchBillingStatus() {
    try {
      const res = await fetch(`${API_BASE}/billing/status`, {
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error("Failed to load billing status");
      const data = await res.json();
      setBilling(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleUpgrade() {
    setCheckoutLoading(true);
    try {
      const res = await fetch(`${API_BASE}/billing/checkout`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to start checkout");
      }
      const { url } = await res.json();
      window.location.href = url;
    } catch (e) {
      setError(String(e));
      setCheckoutLoading(false);
    }
  }

  return (
    <main className="max-w-2xl mx-auto p-8">
      <h1 className="text-2xl font-bold text-white mb-2">Settings</h1>
      <p className="text-gray-400 text-sm mb-8">Manage your account and billing.</p>

      {upgraded === "1" && (
        <div className="mb-6 bg-green-900/40 border border-green-700 rounded-xl p-4 flex items-center gap-3">
          <span className="text-2xl">🎉</span>
          <div>
            <p className="text-green-300 font-semibold">You&apos;re on Pro!</p>
            <p className="text-green-400 text-sm">Unlimited evaluations are now unlocked.</p>
          </div>
        </div>
      )}
      {upgraded === "0" && (
        <div className="mb-6 bg-yellow-900/30 border border-yellow-700 rounded-xl p-4">
          <p className="text-yellow-300 text-sm">Upgrade cancelled. You&apos;re still on the Free plan.</p>
        </div>
      )}

      {error && (
        <div className="mb-6 bg-red-900/30 border border-red-700 rounded-xl p-4">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-300">Current Plan</h2>
          {loading ? (
            <div className="h-6 w-16 bg-gray-700 rounded animate-pulse" />
          ) : billing?.is_pro ? (
            <span className="bg-emerald-900/50 text-emerald-300 border border-emerald-700 text-xs font-bold px-3 py-1 rounded-full">PRO ✓</span>
          ) : (
            <span className="bg-gray-700 text-gray-300 text-xs font-bold px-3 py-1 rounded-full">FREE</span>
          )}
        </div>

        {loading ? (
          <div className="space-y-2">
            <div className="h-4 w-48 bg-gray-800 rounded animate-pulse" />
            <div className="h-4 w-32 bg-gray-800 rounded animate-pulse" />
          </div>
        ) : billing?.is_pro ? (
          <div className="space-y-2 text-sm text-gray-400">
            <p>✅ Unlimited evaluation runs</p>
            <p>✅ All judge models (Claude, Groq, Ollama)</p>
            <p>✅ RAG metrics (faithfulness, context precision, answer relevance)</p>
            <p>✅ Dataset versioning &amp; diff</p>
            <p>✅ Priority support</p>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="space-y-2 text-sm text-gray-400">
              <p>✅ 5 evaluation runs</p>
              <p>✅ All judge models</p>
              <p>✅ RAG metrics</p>
              <p className="text-gray-600">❌ Unlimited runs</p>
              <p className="text-gray-600">❌ Dataset versioning</p>
            </div>
            <div className="mt-4 pt-4 border-t border-gray-700">
              <div className="flex items-baseline gap-2 mb-3">
                <span className="text-3xl font-bold text-white">$29</span>
                <span className="text-gray-400 text-sm">/month</span>
              </div>
              <button
                onClick={handleUpgrade}
                disabled={checkoutLoading}
                className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-lg text-sm transition-colors"
              >
                {checkoutLoading ? "Redirecting to Stripe…" : "Upgrade to Pro →"}
              </button>
              <p className="text-xs text-gray-500 mt-2 text-center">Secure checkout via Stripe. Cancel anytime.</p>
            </div>
          </div>
        )}
      </div>

      {billing && (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-gray-300 mb-3">Account</h2>
          <p className="text-sm text-gray-400">
            Email: <span className="text-white">{billing.email}</span>
          </p>
        </div>
      )}
    </main>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={
      <main className="max-w-2xl mx-auto p-8">
        <div className="h-8 w-32 bg-gray-800 rounded animate-pulse mb-4" />
        <div className="h-4 w-64 bg-gray-800 rounded animate-pulse" />
      </main>
    }>
      <SettingsContent />
    </Suspense>
  );
}

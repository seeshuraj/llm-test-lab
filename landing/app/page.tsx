import Link from "next/link";
import WaitlistFormClient from "./WaitlistFormClient";

const APP_URL = "https://llm-test-lab-app.vercel.app";

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-gray-950 text-white">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-gray-800 max-w-6xl mx-auto">
        <span className="text-xl font-bold text-white">🧪 LLM Test Lab</span>
        <div className="flex items-center gap-4">
          <a href="#features" className="text-gray-400 hover:text-white text-sm transition-colors">Features</a>
          <a href="#compare" className="text-gray-400 hover:text-white text-sm transition-colors">Compare</a>
          <a href="#pricing" className="text-gray-400 hover:text-white text-sm transition-colors">Pricing</a>
          <a href="#how" className="text-gray-400 hover:text-white text-sm transition-colors">How it works</a>
          <a
            href={APP_URL}
            target="_blank"
            className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            Open App →
          </a>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-8 pt-24 pb-20 text-center">
        <div className="inline-flex items-center gap-2 bg-blue-950 border border-blue-700 text-blue-300 text-xs font-medium px-3 py-1 rounded-full mb-6">
          🚀 Now in early access — RAG metrics just shipped
        </div>
        <h1 className="text-5xl font-bold leading-tight mb-6">
          Evaluate your AI app<br />
          <span className="text-blue-400">before your users do</span>
        </h1>
        <p className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto">
          LLM Test Lab runs automated evaluations on any RAG pipeline or AI agent — scoring answers on faithfulness, relevancy, and grounding. Catch regressions before they reach production.
        </p>
        <div className="flex items-center justify-center gap-4 flex-wrap">
          <a
            href={APP_URL}
            target="_blank"
            className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-lg font-medium transition-colors"
          >
            Start Evaluating Free →
          </a>
          <a href="https://github.com/seeshuraj/llm-test-lab" target="_blank" className="bg-gray-800 hover:bg-gray-700 text-white px-6 py-3 rounded-lg font-medium transition-colors">
            ⭐ Star on GitHub
          </a>
        </div>
        {/* Metric preview bar */}
        <div className="mt-14 bg-gray-900 border border-gray-700 rounded-xl p-6 text-left max-w-2xl mx-auto">
          <div className="text-xs text-gray-500 mb-4 uppercase tracking-widest">Example run — RAG metrics</div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "Faithfulness", value: "0.91", color: "text-green-400" },
              { label: "Context Recall", value: "0.74", color: "text-yellow-400" },
              { label: "Answer Relevancy", value: "0.88", color: "text-green-400" },
              { label: "Context Precision", value: "0.65", color: "text-orange-400" },
            ].map((m) => (
              <div key={m.label} className="text-center">
                <div className={`text-2xl font-bold font-mono ${m.color}`}>{m.value}</div>
                <div className="text-xs text-gray-500 mt-1">{m.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Social proof */}
      <section className="max-w-4xl mx-auto px-8 pb-16 text-center">
        <p className="text-gray-600 text-sm uppercase tracking-widest mb-6">Built for teams using</p>
        <div className="flex flex-wrap justify-center gap-6 text-gray-500 text-sm font-mono">
          <span>OpenAI</span><span>·</span>
          <span>LangChain</span><span>·</span>
          <span>LlamaIndex</span><span>·</span>
          <span>Ollama</span><span>·</span>
          <span>Bedrock</span><span>·</span>
          <span>Azure OpenAI</span>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-6xl mx-auto px-8 py-20 border-t border-gray-800">
        <h2 className="text-3xl font-bold text-center mb-4">Everything you need to ship reliable AI</h2>
        <p className="text-gray-400 text-center mb-14 max-w-xl mx-auto">Stop guessing whether your prompt changes made things better or worse.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            {
              icon: "🔬",
              title: "RAG-Specific Metrics",
              desc: "Faithfulness, Context Recall, Answer Relevancy, Context Precision — four diagnostic scores per scenario so you know exactly what failed.",
              badge: "New",
            },
            {
              icon: "🎯",
              title: "Automated Scoring",
              desc: "LLM-as-judge scores every answer on correctness, grounding, and relevance. No manual review needed.",
            },
            {
              icon: "📈",
              title: "Score Trends",
              desc: "Track average quality score over time per project. See instantly when a new prompt or model degrades performance.",
            },
            {
              icon: "⚖️",
              title: "A/B Comparison",
              desc: "Compare two runs side-by-side with per-scenario score deltas. Know exactly which variant wins.",
            },
            {
              icon: "⚡",
              title: "Real Latency Tracking",
              desc: "Measure your app's actual response time per scenario. Catch slow endpoints before production.",
            },
            {
              icon: "🔌",
              title: "Works With Any App",
              desc: "Point it at any HTTP endpoint. POST a question, get an answer back. No SDK integration required.",
            },
          ].map((f) => (
            <div key={f.title} className="bg-gray-900 border border-gray-700 rounded-xl p-6 relative">
              {f.badge && (
                <span className="absolute top-4 right-4 bg-blue-600 text-white text-xs font-semibold px-2 py-0.5 rounded-full">
                  {f.badge}
                </span>
              )}
              <div className="text-3xl mb-3">{f.icon}</div>
              <h3 className="text-white font-semibold mb-2">{f.title}</h3>
              <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Comparison table */}
      <section id="compare" className="max-w-4xl mx-auto px-8 py-20 border-t border-gray-800">
        <h2 className="text-3xl font-bold text-center mb-4">How we compare</h2>
        <p className="text-gray-400 text-center mb-12 max-w-xl mx-auto">The only tool that combines RAG metrics, A/B testing, and latency tracking in one simple UI.</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-3 text-gray-400 font-medium w-48">Feature</th>
                <th className="text-center py-3 text-blue-400 font-semibold">LLM Test Lab</th>
                <th className="text-center py-3 text-gray-400 font-medium">Ragas</th>
                <th className="text-center py-3 text-gray-400 font-medium">Langfuse</th>
              </tr>
            </thead>
            <tbody>
              {[
                ["RAG metrics (4 dimensions)", "✅", "✅", "❌"],
                ["Visual dashboard / UI", "✅", "❌", "✅"],
                ["A/B run comparison", "✅", "❌", "⚠️ Manual"],
                ["Latency tracking", "✅", "❌", "✅"],
                ["Custom rubric per run", "✅", "❌", "❌"],
                ["No-code scenario upload", "✅", "❌", "❌"],
                ["Free tier", "✅", "✅ OSS", "✅"],
              ].map(([feature, ours, ragas, langfuse]) => (
                <tr key={feature as string} className="border-b border-gray-800 hover:bg-gray-900 transition-colors">
                  <td className="py-3 text-gray-300">{feature}</td>
                  <td className="py-3 text-center">{ours}</td>
                  <td className="py-3 text-center text-gray-400">{ragas}</td>
                  <td className="py-3 text-center text-gray-400">{langfuse}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="max-w-4xl mx-auto px-8 py-20 border-t border-gray-800">
        <h2 className="text-3xl font-bold text-center mb-14">How it works</h2>
        <div className="space-y-8">
          {[
            { step: "01", title: "Write your scenarios", desc: "Define questions, expected context, and what a good answer looks like in a simple YAML file." },
            { step: "02", title: "Point it at your app", desc: "Give LLM Test Lab your app's endpoint URL. It sends each question and collects the real answers." },
            { step: "03", title: "Get scored instantly", desc: "An LLM judge scores every answer 0–1 across 4 RAG dimensions. Results appear in your dashboard in seconds." },
            { step: "04", title: "Track and improve", desc: "Run evaluations on every change. Watch your trend chart go up. Catch regressions before users do." },
          ].map((s) => (
            <div key={s.step} className="flex gap-6 items-start">
              <div className="text-blue-500 font-bold text-2xl font-mono w-10 shrink-0">{s.step}</div>
              <div>
                <h3 className="text-white font-semibold mb-1">{s.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="max-w-5xl mx-auto px-8 py-20 border-t border-gray-800">
        <h2 className="text-3xl font-bold text-center mb-4">Simple, transparent pricing</h2>
        <p className="text-gray-400 text-center mb-14 max-w-xl mx-auto">Start free. Upgrade when you need more.</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            {
              name: "Free",
              price: "$0",
              period: "forever",
              desc: "For individuals evaluating side projects.",
              features: ["50 scenarios / month", "Unlimited projects", "A/B comparison", "7-day history"],
              cta: "Start Free",
              href: APP_URL,
              highlight: false,
            },
            {
              name: "Pro",
              price: "$19",
              period: "/ month",
              desc: "For developers shipping production AI apps.",
              features: ["2,000 scenarios / month", "RAG metrics (4 dimensions)", "Latency tracking", "90-day history", "Shareable run links"],
              cta: "Get Pro",
              href: "#waitlist",
              highlight: true,
            },
            {
              name: "Teams",
              price: "$49",
              period: "/ month",
              desc: "For teams running evals across multiple apps.",
              features: ["Unlimited scenarios", "Everything in Pro", "Team workspace", "1-year history", "Priority support"],
              cta: "Get Teams",
              href: "#waitlist",
              highlight: false,
            },
          ].map((plan) => (
            <div
              key={plan.name}
              className={`rounded-xl p-6 border ${
                plan.highlight
                  ? "border-blue-500 bg-blue-950/30"
                  : "border-gray-700 bg-gray-900"
              }`}
            >
              {plan.highlight && (
                <div className="text-blue-400 text-xs font-semibold uppercase tracking-widest mb-3">Most Popular</div>
              )}
              <div className="text-lg font-bold text-white mb-1">{plan.name}</div>
              <div className="flex items-baseline gap-1 mb-2">
                <span className="text-3xl font-bold text-white">{plan.price}</span>
                <span className="text-gray-400 text-sm">{plan.period}</span>
              </div>
              <p className="text-gray-400 text-sm mb-6">{plan.desc}</p>
              <ul className="space-y-2 mb-8">
                {plan.features.map((f) => (
                  <li key={f} className="text-gray-300 text-sm flex items-start gap-2">
                    <span className="text-green-400 mt-0.5">✓</span> {f}
                  </li>
                ))}
              </ul>
              <a
                href={plan.href}
                target={plan.href.startsWith("http") ? "_blank" : undefined}
                className={`block text-center py-2.5 rounded-lg font-medium text-sm transition-colors ${
                  plan.highlight
                    ? "bg-blue-600 hover:bg-blue-500 text-white"
                    : "bg-gray-700 hover:bg-gray-600 text-white"
                }`}
              >
                {plan.cta}
              </a>
            </div>
          ))}
        </div>
      </section>

      {/* Waitlist */}
      <section id="waitlist" className="max-w-2xl mx-auto px-8 py-20 border-t border-gray-800 text-center">
        <h2 className="text-3xl font-bold mb-4">Get early access</h2>
        <p className="text-gray-400 mb-8">Be the first to know when LLM Test Lab opens to the public. No spam, ever.</p>
        <WaitlistFormClient />
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 px-8 py-6 text-center text-gray-600 text-sm">
        © 2026 LLM Test Lab · Built by{" "}
        <a href="https://github.com/seeshuraj" className="text-gray-400 hover:text-white transition-colors">
          @seeshuraj
        </a>
        {" · "}
        <a href="https://github.com/seeshuraj/llm-test-lab" className="text-gray-400 hover:text-white transition-colors">
          GitHub
        </a>
      </footer>
    </main>
  );
}

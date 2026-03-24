import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-gray-950 text-white">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-gray-800 max-w-6xl mx-auto">
        <span className="text-xl font-bold text-white">LLM Test Lab</span>
        <div className="flex items-center gap-4">
          <a href="#features" className="text-gray-400 hover:text-white text-sm transition-colors">Features</a>
          <a href="#how" className="text-gray-400 hover:text-white text-sm transition-colors">How it works</a>
          <a href="#waitlist" className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
            Get Early Access
          </a>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-8 pt-24 pb-20 text-center">
        <div className="inline-flex items-center gap-2 bg-blue-950 border border-blue-700 text-blue-300 text-xs font-medium px-3 py-1 rounded-full mb-6">
          🚀 Now in early access
        </div>
        <h1 className="text-5xl font-bold leading-tight mb-6">
          Evaluate your AI app<br />
          <span className="text-blue-400">before your users do</span>
        </h1>
        <p className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto">
          LLM Test Lab lets you run automated evaluations on any RAG pipeline or AI agent — score answers, track quality over time, and catch regressions before they reach production.
        </p>
        <div className="flex items-center justify-center gap-4">
          <a href="#waitlist" className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-lg font-medium transition-colors">
            Join the Waitlist
          </a>
          <a href="https://github.com/seeshuraj/llm-test-lab" target="_blank" className="bg-gray-800 hover:bg-gray-700 text-white px-6 py-3 rounded-lg font-medium transition-colors">
            ⭐ Star on GitHub
          </a>
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
            {
              icon: "🔐",
              title: "Multi-tenant & Secure",
              desc: "Each user sees only their own runs. JWT auth with full user isolation out of the box.",
            },
          ].map((f) => (
            <div key={f.title} className="bg-gray-900 border border-gray-700 rounded-xl p-6">
              <div className="text-3xl mb-3">{f.icon}</div>
              <h3 className="text-white font-semibold mb-2">{f.title}</h3>
              <p className="text-gray-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="max-w-4xl mx-auto px-8 py-20 border-t border-gray-800">
        <h2 className="text-3xl font-bold text-center mb-14">How it works</h2>
        <div className="space-y-8">
          {[
            { step: "01", title: "Write your scenarios", desc: "Define questions, expected context, and what a good answer looks like in a simple YAML file." },
            { step: "02", title: "Point it at your app", desc: "Give LLM Test Lab your app's endpoint URL. It sends each question and collects the real answers." },
            { step: "03", title: "Get scored instantly", desc: "An LLM judge scores every answer 0–1 with a written reason. Results appear in your dashboard in seconds." },
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

      {/* Waitlist */}
      <section id="waitlist" className="max-w-2xl mx-auto px-8 py-20 border-t border-gray-800 text-center">
        <h2 className="text-3xl font-bold mb-4">Get early access</h2>
        <p className="text-gray-400 mb-8">Be the first to know when LLM Test Lab opens to the public. No spam, ever.</p>
        <WaitlistForm />
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 px-8 py-6 text-center text-gray-600 text-sm">
        © 2026 LLM Test Lab · Built by{" "}
        <a href="https://github.com/seeshuraj" className="text-gray-400 hover:text-white transition-colors">
          @seeshuraj
        </a>
      </footer>
    </main>
  );
}

function WaitlistForm() {
  "use client";
  return <WaitlistFormClient />;
}

// Keep form in separate client component
import WaitlistFormClient from "./WaitlistFormClient";

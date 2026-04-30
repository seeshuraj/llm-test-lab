import WaitlistFormClient from "./WaitlistFormClient";

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "https://llm-test-lab-app.vercel.app";
const STRIPE_PRO_URL = process.env.NEXT_PUBLIC_STRIPE_PRO_URL ?? "#pricing";
const STRIPE_TEAMS_URL = process.env.NEXT_PUBLIC_STRIPE_TEAMS_URL ?? "#pricing";

// ----------------------------------------------------------------------------
// SVG icon components — simple 24px line icons, no external dep
// ----------------------------------------------------------------------------
function IconBarChart() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.5V19m4.5-9.5V19m4.5-13V19m4.5 4.5V9m4.5-5v15" />
    </svg>
  );
}
function IconShield() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
    </svg>
  );
}
function IconTrendUp() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941" />
    </svg>
  );
}
function IconSplit() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
    </svg>
  );
}
function IconClock() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
    </svg>
  );
}
function IconPlug() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" />
    </svg>
  );
}

// SVG flask logo — replaces the emoji
function FlaskLogo({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 3h6M9 3v7L4.5 18a1 1 0 0 0 .9 1.5h13.2a1 1 0 0 0 .9-1.5L15 10V3" />
      <circle cx="9" cy="16" r="1" fill="#60a5fa" stroke="none" />
      <circle cx="14" cy="14" r="0.75" fill="#34d399" stroke="none" />
    </svg>
  );
}

const features = [
  {
    icon: <IconBarChart />,
    title: "RAG-specific metrics",
    desc: "Faithfulness, Context Recall, Answer Relevancy, Context Precision — four diagnostic scores per scenario. One number tells you nothing. Four tell you exactly where it broke.",
    badge: "New",
  },
  {
    icon: <IconShield />,
    title: "LLM-as-judge scoring",
    desc: "No hand-written assertions. An LLM judge reads your rubric and grades each answer 0–1. Works on open-ended questions that regex can\'t touch.",
  },
  {
    icon: <IconTrendUp />,
    title: "Score trends over time",
    desc: "Every run is logged. Watch a chart of your average score across every commit. You\'ll know the exact moment a prompt change or model upgrade helped or hurt.",
  },
  {
    icon: <IconSplit />,
    title: "A/B run comparison",
    desc: "Pick any two runs and diff them scenario-by-scenario. Green means improvement, red means regression. No spreadsheet required.",
  },
  {
    icon: <IconClock />,
    title: "Real latency measurement",
    desc: "Scores your app\'s actual response time per scenario, not a synthetic benchmark. P95 outliers show up before your users file tickets.",
  },
  {
    icon: <IconPlug />,
    title: "Any stack, any endpoint",
    desc: "POST a question, get an answer back. That\'s the entire integration. LangChain, LlamaIndex, raw OpenAI, home-grown FastAPI — all work out of the box.",
  },
];

const steps = [
  {
    n: "1",
    title: "Write scenarios in YAML",
    desc: "Describe a question, the context your retriever should use, and what a correct answer looks like. Five lines per scenario.",
    code: `- id: return_policy
  question: "What is the return window?"
  context_docs:
    - "Items can be returned within 30 days."
  expected_keywords: ["30 days"]`,
  },
  {
    n: "2",
    title: "Point it at your app",
    desc: "Your app needs one route: POST /answer → { answer }. LLM Test Lab sends each question and collects real responses.",
    code: `python cli/llm_eval.py \\
  --api-url $BACKEND \\
  --app-url https://your-app.com/answer \\
  --scenarios scenarios.yaml`,
  },
  {
    n: "3",
    title: "Get scored, catch regressions",
    desc: "Results appear in your dashboard in seconds. Set --fail-under 0.7 in CI and the build breaks before bad code reaches users.",
    code: `✔ s1 [0.91] return_policy
✔ s2 [0.88] shipping_time
⚠ s3 [0.54] cancellation  ← investigate
Avg: 0.78 ≥ 0.70 ✔ PASSED`,
  },
];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-[#0a0a0f] text-white">

      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-[#0a0a0f]/90 backdrop-blur border-b border-white/5">
        <div className="max-w-6xl mx-auto flex items-center justify-between px-6 py-4">
          <a href="/" className="flex items-center gap-2 text-white hover:opacity-80 transition-opacity">
            <span className="text-blue-400"><FlaskLogo size={20} /></span>
            <span className="font-semibold text-sm tracking-tight">LLM Test Lab</span>
          </a>
          <div className="flex items-center gap-6">
            <a href="#features" className="text-gray-500 hover:text-gray-200 text-sm transition-colors hidden sm:block">Features</a>
            <a href="#how" className="text-gray-500 hover:text-gray-200 text-sm transition-colors hidden sm:block">How it works</a>
            <a href="#pricing" className="text-gray-500 hover:text-gray-200 text-sm transition-colors hidden sm:block">Pricing</a>
            <a
              href="https://github.com/seeshuraj/llm-test-lab"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-500 hover:text-gray-200 text-sm transition-colors hidden sm:block"
            >
              GitHub
            </a>
            <a
              href={APP_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="bg-white text-gray-900 hover:bg-gray-100 px-4 py-1.5 rounded-md text-sm font-medium transition-colors"
            >
              Open app
            </a>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 pt-28 pb-24 text-center">
        <a
          href="https://github.com/seeshuraj/llm-test-lab"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 text-xs text-gray-400 border border-white/10 hover:border-white/20 bg-white/5 px-3 py-1.5 rounded-full mb-8 transition-colors"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          Open source · MIT licence · v0.1
        </a>

        <h1 className="text-5xl sm:text-6xl font-bold leading-[1.1] tracking-tight mb-6">
          Your LLM looked fine<br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">
            in the notebook.
          </span>
        </h1>
        <p className="text-lg text-gray-400 mb-4 max-w-xl mx-auto leading-relaxed">
          LLM Test Lab runs automated evals on any RAG pipeline or AI agent.
          Write scenarios in YAML, run them in CI, catch regressions before
          your users do.
        </p>
        <p className="text-sm text-gray-600 mb-10">
          Works with any HTTP endpoint — no SDK, no vendor lock-in.
        </p>

        <div className="flex items-center justify-center gap-3 flex-wrap">
          <a
            href={APP_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-lg font-medium text-sm transition-colors"
          >
            Start evaluating free
          </a>
          <a
            href="https://github.com/seeshuraj/llm-test-lab"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 bg-white/5 border border-white/10 hover:bg-white/10 text-gray-300 px-6 py-3 rounded-lg font-medium text-sm transition-colors"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
            </svg>
            Star on GitHub
          </a>
        </div>

        {/* Terminal-style metric preview */}
        <div className="mt-16 bg-[#111118] border border-white/8 rounded-xl overflow-hidden text-left max-w-2xl mx-auto shadow-2xl">
          <div className="flex items-center gap-1.5 px-4 py-3 border-b border-white/5 bg-white/3">
            <span className="w-3 h-3 rounded-full bg-red-500/70" />
            <span className="w-3 h-3 rounded-full bg-yellow-500/70" />
            <span className="w-3 h-3 rounded-full bg-green-500/70" />
            <span className="ml-3 text-xs text-gray-600 font-mono">llm_eval.py — rag-qa run</span>
          </div>
          <div className="px-5 py-5 font-mono text-xs leading-7 text-gray-400">
            <div><span className="text-gray-600">$</span> <span className="text-gray-300">python cli/llm_eval.py --scenarios rag-qa.yaml --fail-under 0.7</span></div>
            <div className="mt-1 text-gray-600">⏳ Running 5 scenarios against your app...</div>
            <div className="mt-2">
              <span className="text-green-400">✔</span> <span className="text-gray-500">[0.91]</span> factual_recall
              <span className="ml-3 text-gray-600 text-xs">312ms</span>
            </div>
            <div>
              <span className="text-green-400">✔</span> <span className="text-gray-500">[0.88]</span> multi_doc_synthesis
              <span className="ml-3 text-gray-600 text-xs">445ms</span>
            </div>
            <div>
              <span className="text-yellow-400">⚠</span> <span className="text-gray-500">[0.54]</span> hallucination_check
              <span className="ml-3 text-gray-600 text-xs">389ms ← investigate</span>
            </div>
            <div>
              <span className="text-green-400">✔</span> <span className="text-gray-500">[0.82]</span> out_of_scope
              <span className="ml-3 text-gray-600 text-xs">201ms</span>
            </div>
            <div>
              <span className="text-green-400">✔</span> <span className="text-gray-500">[0.79]</span> exact_quote
              <span className="ml-3 text-gray-600 text-xs">356ms</span>
            </div>
            <div className="mt-3 pt-3 border-t border-white/5">
              <span className="text-gray-500">Avg score: </span><span className="text-blue-400 font-bold">0.79</span>
              <span className="text-gray-600 ml-4">≥ 0.70</span>
              <span className="text-green-400 ml-2 font-bold">✔ PASSED</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-6xl mx-auto px-6 py-24 border-t border-white/5">
        <div className="max-w-xl mx-auto text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">What you actually get</h2>
          <p className="text-gray-500 text-sm leading-relaxed">
            Not another wrapper around OpenAI Evals. Built specifically for teams shipping RAG
            pipelines and AI agents to production.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {features.map((f) => (
            <div key={f.title} className="group bg-white/3 hover:bg-white/5 border border-white/8 hover:border-white/12 rounded-xl p-6 relative transition-all">
              {f.badge && (
                <span className="absolute top-4 right-4 bg-blue-600/20 text-blue-400 border border-blue-500/30 text-xs font-medium px-2 py-0.5 rounded-full">
                  {f.badge}
                </span>
              )}
              <div className="text-blue-400 mb-4 p-2 bg-blue-400/10 rounded-lg w-fit">
                {f.icon}
              </div>
              <h3 className="text-white font-semibold mb-2 text-sm">{f.title}</h3>
              <p className="text-gray-500 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="max-w-4xl mx-auto px-6 py-24 border-t border-white/5">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">From zero to evals in 5 minutes</h2>
          <p className="text-gray-500 text-sm">No infra to deploy. No API keys to configure except your own backend.</p>
        </div>
        <div className="space-y-10">
          {steps.map((s) => (
            <div key={s.n} className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
              <div>
                <div className="flex items-center gap-3 mb-3">
                  <span className="w-7 h-7 rounded-full bg-blue-600/20 border border-blue-500/30 text-blue-400 text-xs font-bold flex items-center justify-center shrink-0">
                    {s.n}
                  </span>
                  <h3 className="font-semibold text-white">{s.title}</h3>
                </div>
                <p className="text-gray-500 text-sm leading-relaxed pl-10">{s.desc}</p>
              </div>
              <div className="bg-[#111118] border border-white/8 rounded-lg p-4 font-mono text-xs text-gray-400 leading-6 whitespace-pre overflow-x-auto">
                {s.code}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="max-w-5xl mx-auto px-6 py-24 border-t border-white/5">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">Pricing</h2>
          <p className="text-gray-500 text-sm">Free to start. No credit card needed.</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {[
            {
              name: "Free",
              price: "$0",
              period: "forever",
              desc: "Good for side projects and getting started.",
              features: ["50 scenarios / month", "Unlimited projects", "A/B comparison", "7-day history"],
              cta: "Start free",
              href: APP_URL,
              highlight: false,
            },
            {
              name: "Pro",
              price: "$19",
              period: "/ month",
              desc: "For developers who ship AI features to production.",
              features: ["2,000 scenarios / month", "RAG metrics (4 dimensions)", "Latency tracking", "90-day history", "Shareable run links"],
              cta: "Upgrade to Pro",
              href: STRIPE_PRO_URL,
              highlight: true,
            },
            {
              name: "Teams",
              price: "$49",
              period: "/ month",
              desc: "For teams running evals across multiple apps.",
              features: ["Unlimited scenarios", "Everything in Pro", "Team workspace", "1-year history", "Priority support"],
              cta: "Upgrade to Teams",
              href: STRIPE_TEAMS_URL,
              highlight: false,
            },
          ].map((plan) => (
            <div
              key={plan.name}
              className={`rounded-xl p-6 border relative ${
                plan.highlight
                  ? "border-blue-500/50 bg-blue-950/20"
                  : "border-white/8 bg-white/3"
              }`}
            >
              {plan.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-blue-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
                    Most popular
                  </span>
                </div>
              )}
              <div className="text-sm font-semibold text-gray-300 mb-1">{plan.name}</div>
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-3xl font-bold text-white">{plan.price}</span>
                <span className="text-gray-500 text-sm">{plan.period}</span>
              </div>
              <p className="text-gray-600 text-xs mb-6 leading-relaxed">{plan.desc}</p>
              <ul className="space-y-2.5 mb-8">
                {plan.features.map((f) => (
                  <li key={f} className="text-gray-400 text-sm flex items-center gap-2">
                    <svg className="w-3.5 h-3.5 text-green-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                    </svg>
                    {f}
                  </li>
                ))}
              </ul>
              <a
                href={plan.href}
                target={plan.href.startsWith("http") ? "_blank" : undefined}
                rel={plan.href.startsWith("http") ? "noopener noreferrer" : undefined}
                className={`block text-center py-2.5 rounded-lg font-medium text-sm transition-colors ${
                  plan.highlight
                    ? "bg-blue-600 hover:bg-blue-500 text-white"
                    : "bg-white/8 hover:bg-white/12 text-gray-200"
                }`}
              >
                {plan.cta}
              </a>
            </div>
          ))}
        </div>
        <p className="text-center text-gray-700 text-xs mt-8">Payments processed by Stripe. Cancel any time.</p>
      </section>

      {/* Waitlist */}
      <section id="waitlist" className="max-w-lg mx-auto px-6 py-24 border-t border-white/5 text-center">
        <h2 className="text-2xl font-bold mb-3">Stay in the loop</h2>
        <p className="text-gray-500 text-sm mb-8 leading-relaxed">
          New features ship regularly. Drop your email and I’ll let you know
          when something worth knowing about lands.
        </p>
        <WaitlistFormClient />
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 px-6 py-8">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4 text-gray-600 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-blue-400/60"><FlaskLogo size={14} /></span>
            <span>LLM Test Lab</span>
            <span className="text-gray-800">·</span>
            <span>Built with FastAPI + Next.js</span>
          </div>
          <div className="flex items-center gap-4">
            <a href="https://github.com/seeshuraj" className="hover:text-gray-300 transition-colors">@seeshuraj</a>
            <a href="https://github.com/seeshuraj/llm-test-lab" className="hover:text-gray-300 transition-colors">GitHub</a>
            <a href={APP_URL} target="_blank" rel="noopener noreferrer" className="hover:text-gray-300 transition-colors">Open app</a>
          </div>
        </div>
      </footer>
    </main>
  );
}

# 🧪 LLM Test Lab

> **Catch AI regressions before your users do.**  
> Automated evaluation for RAG pipelines and LLM endpoints — no SDK required.

[![CI](https://github.com/seeshuraj/llm-test-lab/actions/workflows/llm-eval.yml/badge.svg)](https://github.com/seeshuraj/llm-test-lab/actions/workflows/llm-eval.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub Marketplace](https://img.shields.io/badge/Marketplace-LLM%20Test%20Lab%20Eval-blue?logo=github)](https://github.com/marketplace/actions/llm-test-lab-eval)
[![GitHub stars](https://img.shields.io/github/stars/seeshuraj/llm-test-lab?style=social)](https://github.com/seeshuraj/llm-test-lab/stargazers)

**LLM Test Lab** is an open-source LLM evaluation platform. Write scenarios in YAML, point it at any HTTP endpoint, and get automated quality scores — faithfulness, relevancy, grounding — tracked over time and wired into your CI pipeline.

Built for AI engineers and teams shipping RAG apps, chatbots, and LLM-powered features who need a fast, framework-agnostic way to catch quality regressions **before** they reach production.

🌐 **Landing:** [llm-test-lab-landing.vercel.app](https://llm-test-lab-landing.vercel.app)  
📊 **Dashboard:** [llm-test-lab-app.vercel.app](https://llm-test-lab-app.vercel.app)  
📦 **API:** [llm-test-lab.fly.dev/health](https://llm-test-lab.fly.dev/health)  
🛒 **GitHub Action:** [marketplace/actions/llm-test-lab-eval](https://github.com/marketplace/actions/llm-test-lab-eval)

---

## 🎬 See It in Action

**Dashboard**

![LLM Test Lab Dashboard](LLM-Test-Lab.gif)

**Landing Page**

![LLM Test Lab Landing Page](Landing-Page.gif)

---

## Why LLM Test Lab?

You wouldn't ship backend code without tests. But most teams ship LLM changes with zero automated quality checks.

When you swap a model, tweak a prompt, or change your retrieval logic — **how do you know if it got better or worse?**

LLM Test Lab answers that question systematically:

- ✅ Define what "good" looks like in a YAML file
- ✅ Run automated scoring against any endpoint after every deploy
- ✅ Track score trends over time so regressions surface immediately
- ✅ Fail your CI build if quality drops below your threshold

No vendor lock-in. No SDK integration. Works with any RAG pipeline, LangChain app, or custom LLM endpoint.

---

## ✨ Features

| Feature | Description |
|---|---|
| **RAG metrics** | Faithfulness, Answer Relevancy, Context Precision, Context Recall |
| **LLM-as-judge** | Automated 0–1 scores via Groq (Llama 3.1 / 3.3) |
| **Score trend charts** | Visual quality history per project and per scenario |
| **A/B run comparison** | Side-by-side score deltas between any two runs |
| **Latency tracking** | Real response time per scenario, per run |
| **CI/CD integration** | GitHub Action — fail builds on score regression |
| **HTTP-first** | Works with any endpoint — no SDK, no code changes |
| **Slack alerts** | Notify your team when scores drop below threshold |
| **Auth + projects** | Multi-user dashboard, JWT auth, per-project run history |

---

## ⚡ Quickstart

### 1. Clone and run locally (5 minutes)

```bash
git clone https://github.com/seeshuraj/llm-test-lab.git
cd llm-test-lab

# Backend
cp apps/backend/.env.example apps/backend/.env
# → Add your GROQ_API_KEY to .env
pip install -r apps/backend/requirements.txt
uvicorn apps.backend.app.main:app --reload
```

```bash
# Frontend (new terminal)
cd apps/frontend
cp .env.example .env.local
npm install && npm run dev
```

Open [http://localhost:3000](http://localhost:3000) → sign up → click **+ New Run**.

---

### 2. Write your first scenario

Create a `scenarios.yaml` pointing at your AI endpoint:

```yaml
scenarios:
  - id: s1
    question: "What is the refund policy?"
    context: "Customers can request refunds within 30 days of purchase."
    endpoint: "https://your-ai-app.com/answer"
    tags: [refund, policy]

  - id: s2
    question: "How do I reset my password?"
    context: "Go to Settings → Security → Reset Password."
    endpoint: "https://your-ai-app.com/answer"
    tags: [auth, onboarding]
```

Run it:

```bash
python cli/llm_eval.py \
  --scenarios scenarios.yaml \
  --api-url https://llm-test-lab.fly.dev \
  --token YOUR_TOKEN
```

You'll get a run ID and scores immediately. View the full breakdown in the dashboard.

---

### 3. Add to CI — fail builds on regressions

```yaml
# .github/workflows/eval.yml
name: LLM Quality Gate
on: [push]

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: seeshuraj/llm-test-lab@v1
        with:
          api-url: ${{ vars.LLM_TEST_LAB_API_URL }}
          token:   ${{ secrets.LLM_TEST_LAB_TOKEN }}
          app-url: https://your-ai-app.com/answer
          scenarios: scenarios.yaml
          fail-under: '0.7'   # ← CI fails if avg score drops below this
```

**GitHub Action inputs:**

| Input | Required | Default | Description |
|---|---|---|---|
| `api-url` | ✅ | — | LLM Test Lab backend URL |
| `token` | ✅ | — | API token from your dashboard |
| `app-url` | ✅ | — | Your AI app's answer endpoint |
| `scenarios` | — | `scenarios.yaml` | Path to scenarios file |
| `project` | — | `my-project` | Project name for grouping runs |
| `model` | — | `llama-3.1-8b-instant` | Judge model (Groq) |
| `fail-under` | — | `0.6` | Fail CI if avg score drops below this |

---

## 🏗️ Architecture

```
llm-test-lab/
├── action.yml                  # Reusable GitHub Action (Marketplace)
├── apps/
│   ├── backend/                # FastAPI scoring engine + REST API  → Fly.io
│   └── frontend/               # Next.js dashboard (auth, runs, trends, A/B) → Vercel
├── packages/
│   ├── core-python/            # Shared Python judges + scoring logic
│   └── sdk-python/             # Python SDK
├── cli/
│   └── llm_eval.py             # CI script called by action.yml
├── scenarios.yaml              # Example scenario file
└── .github/workflows/          # CI: unit tests + LLM eval on push
```

| Layer | Stack | Hosting |
|---|---|---|
| Frontend | Next.js 16, TypeScript, Tailwind CSS | Vercel |
| Backend | FastAPI, Python 3.11, SQLAlchemy | Fly.io |
| Database | PostgreSQL | Supabase |
| AI / Judge | Groq — Llama 3.1 8B, Llama 3.3 70B | — |
| Auth | JWT (python-jose + bcrypt) | — |
| Alerts | Slack Webhooks, Resend (email) | — |

---

## 🔑 Environment Variables

### Backend (`apps/backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ | Get at [console.groq.com](https://console.groq.com) |
| `SUPABASE_DB_URL` | ✅ | `postgresql://postgres:[pass]@db.[ref].supabase.co:5432/postgres` |
| `SECRET_KEY` | ✅ | `openssl rand -hex 32` |
| `CORS_ALLOWED_ORIGINS` | ✅ | Comma-separated frontend URLs |
| `SLACK_WEBHOOK_URL` | optional | Slack alerts on score regression |
| `RESEND_API_KEY` | optional | Email alerts via [resend.com](https://resend.com) |

> **No Supabase?** If `SUPABASE_DB_URL` is unset, the backend falls back to SQLite automatically — great for local dev.

### Frontend (`apps/frontend/.env.local`)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend URL, e.g. `https://llm-test-lab.fly.dev` |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key |

---

## 📊 Roadmap

- [x] Multi-model eval engine
- [x] LLM-as-judge scoring (Groq — Llama 3.1 / 3.3)
- [x] RAG evaluation metrics (faithfulness, relevancy, precision, recall)
- [x] Score history + trend charts
- [x] Auth + per-user dashboards
- [x] A/B run comparison
- [x] CI/CD GitHub Action (`uses: seeshuraj/llm-test-lab@v1`)
- [x] Slack alerts on score regression
- [x] Deployed on Fly.io (always-on)
- [ ] Live demo (no signup required)
- [ ] Claude as judge (alongside Groq)
- [ ] Threshold alerts + drift detection
- [ ] PyPI SDK package (`pip install llm-test-lab`)
- [ ] Stripe billing (Free / Pro / Teams)

---

## 🤝 Contributing

Contributions are welcome — especially:

- New eval metrics (G-Eval, RAGAS-style, custom rubrics)
- Scenario templates for common RAG use-cases
- SDK improvements (Python, JS)
- Bug fixes and docs

See [CONTRIBUTING.md](CONTRIBUTING.md) to get started. If you're unsure where to begin, open an issue and say hi.

---

## 📄 License

[MIT](LICENSE) © 2026 [Seeshuraj Bhoopalan](https://github.com/seeshuraj)

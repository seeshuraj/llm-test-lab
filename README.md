# 🧪 LLM Test Lab

> Evaluate your AI app before your users do.

[![CI](https://github.com/seeshuraj/llm-test-lab/actions/workflows/llm-eval.yml/badge.svg)](https://github.com/seeshuraj/llm-test-lab/actions/workflows/llm-eval.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub Marketplace](https://img.shields.io/badge/Marketplace-LLM%20Test%20Lab%20Eval-blue?logo=github)](https://github.com/marketplace/actions/llm-test-lab-eval)
[![GitHub stars](https://img.shields.io/github/stars/seeshuraj/llm-test-lab?style=social)](https://github.com/seeshuraj/llm-test-lab/stargazers)

LLM Test Lab is an **open-source evaluation platform** for AI apps. Point it at any RAG pipeline or LLM endpoint — it scores every answer on faithfulness, relevancy, and grounding, tracks quality over time, and fails your CI when regressions slip through.

🌐 **Landing Page:** [llm-test-lab-landing.vercel.app](https://llm-test-lab-landing.vercel.app)  
📊 **Live Dashboard:** [llm-test-lab-app.vercel.app](https://llm-test-lab-app.vercel.app)  
📦 **Backend API:** [llm-test-lab-api.fly.dev/health](https://llm-test-lab-api.fly.dev/health)  
🛒 **GitHub Marketplace:** [LLM Test Lab Eval](https://github.com/marketplace/actions/llm-test-lab-eval)

---

## 🎬 Dashboard Demo

![LLM Test Lab Dashboard](LLM-Test-Lab.gif)

---

## 🏠 Landing Page

![LLM Test Lab Landing Page](Landing-Page.gif)

---

## ✨ Features

- **RAG metrics** — Faithfulness, Context Recall, Answer Relevancy, Context Precision
- **LLM-as-judge scoring** — Automated 0–1 scores via Groq (Llama 3.1 / 3.3)
- **Score trend charts** — Track quality over time per project
- **A/B comparison** — Side-by-side score deltas between two runs
- **Latency tracking** — Real response time per scenario
- **CI/CD integration** — GitHub Action that fails your build on regressions
- **Works with any HTTP endpoint** — No SDK required
- **Slack alerts** — Notify your team when scores drop below threshold

---

## ⚡ Quickstart (3 commands)

```bash
git clone https://github.com/seeshuraj/llm-test-lab.git && cd llm-test-lab
pip install -r apps/backend/requirements.txt
cp apps/backend/.env.example apps/backend/.env
# Add GROQ_API_KEY to apps/backend/.env, then:
uvicorn apps.backend.app.main:app --reload
```

Frontend:
```bash
cd apps/frontend && npm install && cp .env.example .env.local && npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and click **+ New Run**.

---

## 🔌 GitHub Action — Add to Any Repo in 10 Lines

```yaml
# .github/workflows/eval.yml
name: LLM Eval
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
          fail-under: '0.7'
```

**Inputs:**

| Input | Required | Default | Description |
|---|---|---|---|
| `api-url` | ✅ | — | Your LLM Test Lab backend URL |
| `token` | ✅ | — | API token from your dashboard |
| `app-url` | ✅ | — | Your AI app's answer endpoint |
| `scenarios` | — | `scenarios.yaml` | Path to scenarios file |
| `project` | — | `my-project` | Project name for grouping runs |
| `model` | — | `llama-3.1-8b-instant` | Judge model |
| `fail-under` | — | `0.6` | Fail CI if avg score drops below this |

---

## 🏗️ Architecture

```
llm-test-lab/
├── action.yml              # Reusable GitHub Action (Marketplace)
├── apps/
│   ├── backend/            # FastAPI scoring engine + REST API (Fly.io)
│   └── frontend/           # Dashboard: auth, runs, compare, trends (Vercel)
├── packages/
│   ├── core-python/        # Shared Python judges + scoring
│   └── sdk-python/         # Python SDK
├── cli/
│   └── llm_eval.py         # CI script invoked by action.yml
└── .github/workflows/      # CI: unit tests + LLM eval on push
```

| Layer | Stack | Host |
|---|---|---|
| Frontend | Next.js, TypeScript, Tailwind | Vercel |
| Backend | FastAPI, Python 3.11 | Fly.io |
| Database | PostgreSQL | Supabase |
| AI / Judges | Groq — Llama 3.1 8B, 3.3 70B | — |

---

## 🔑 Environment Variables

### Backend (Fly.io secrets)

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ | [console.groq.com](https://console.groq.com) |
| `SUPABASE_DB_URL` | ✅ | `postgresql://postgres:[pass]@db.[ref].supabase.co:5432/postgres` |
| `SECRET_KEY` | ✅ | `openssl rand -hex 32` |
| `CORS_ALLOWED_ORIGINS` | ✅ | Comma-separated frontend URLs |
| `SLACK_WEBHOOK_URL` | optional | Slack alerts on score regression |
| `RESEND_API_KEY` | optional | Email alerts via [resend.com](https://resend.com) |

### Frontend (Vercel env vars)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend URL, e.g. `https://llm-test-lab-api.fly.dev` |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key |

> **Local dev:** If `SUPABASE_DB_URL` is not set, backend falls back to SQLite automatically.

---

## 📊 Roadmap

- [x] Multi-model eval engine
- [x] LLM-as-judge scoring (Groq)
- [x] RAG evaluation metrics
- [x] Score history + trend charts
- [x] Auth + personal dashboards
- [x] A/B run comparison
- [x] CI/CD GitHub Action (`uses: seeshuraj/llm-test-lab@v1`)
- [x] Slack alerts on score regression
- [x] Deployed on Fly.io (always-on)
- [ ] Live demo (no signup)
- [ ] Drift detection alerts
- [ ] npm / PyPI SDK packages
- [ ] Stripe billing (Free / Pro / Teams)

---

## 🛠️ Tech Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 16, TypeScript, Tailwind CSS |
| Backend | FastAPI, Python 3.11, SQLAlchemy |
| Database | Supabase (PostgreSQL) / SQLite (local) |
| AI / Judges | Groq — Llama 3.1 8B, Llama 3.3 70B |
| Auth | JWT (python-jose + bcrypt) |
| CI | GitHub Actions |
| Hosting | Fly.io + Vercel |
| Alerts | Slack Webhooks, Resend (email) |

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome — especially new eval metrics, scenario templates, and SDK improvements.

---

## 📄 License

[MIT](LICENSE) © 2026 [Seeshuraj Bhoopalan](https://github.com/seeshuraj)

# 🧪 LLM Test Lab

> Evaluate your AI app before your users do.

[![CI](https://github.com/seeshuraj/llm-test-lab/actions/workflows/llm-eval.yml/badge.svg)](https://github.com/seeshuraj/llm-test-lab/actions/workflows/llm-eval.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/seeshuraj/llm-test-lab?style=social)](https://github.com/seeshuraj/llm-test-lab/stargazers)

LLM Test Lab is an **open-source evaluation platform** for AI apps. Point it at any RAG pipeline or LLM endpoint — it scores every answer on faithfulness, relevancy, and grounding, tracks quality over time, and fails your CI when regressions slip through.

🌐 **Live App:** [llm-test-lab-app.vercel.app](https://llm-test-lab-app.vercel.app)  
🏠 **Landing:** [llm-test-lab-psi.vercel.app](https://llm-test-lab-psi.vercel.app)  
📦 **Backend API:** [llm-test-lab.fly.dev](https://llm-test-lab.fly.dev/health)

---

## ✨ Features

- **RAG metrics** — Faithfulness, Context Recall, Answer Relevancy, Context Precision
- **LLM-as-judge scoring** — Automated 0–1 scores via Groq (Llama 3.1/3.3)
- **Score trend charts** — Track quality over time per project
- **A/B comparison** — Side-by-side score deltas between two runs
- **Latency tracking** — Real response time per scenario
- **CI/CD integration** — GitHub Action that fails your build on regressions
- **Works with any HTTP endpoint** — No SDK required
- **Email alerts** — Notify when score drops below threshold

---

## ⚡ Quickstart (3 commands)

```bash
git clone https://github.com/seeshuraj/llm-test-lab.git && cd llm-test-lab
pip install -r apps/backend/requirements.txt && cp apps/backend/.env.example apps/backend/.env
# Set GROQ_API_KEY in apps/backend/.env, then:
uvicorn apps.backend.app.main:app --reload
```

Frontend:
```bash
cd apps/frontend && npm install && cp .env.example .env.local && npm run dev
```

---

## 🔌 GitHub Action — Add to Your Repo

Add automated evals to **any** repo in 10 lines:

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
├── action.yml              # Reusable GitHub Action
├── landing/                # Next.js landing page (Vercel)
├── apps/
│   ├── backend/            # FastAPI scoring engine + REST API (Fly.io)
│   └── frontend/           # Dashboard: auth, runs, compare, trends (Vercel)
├── packages/
│   ├── core-python/        # Shared Python judges + scoring
│   └── sdk-python/         # Python SDK
├── cli/
│   └── llm_eval.py         # CI script invoked by action.yml
└── .github/workflows/      # CI: unit tests + LLM eval on push to main
```

| Layer | Host |
|---|---|
| Frontend (Next.js) | Vercel |
| Backend (FastAPI) | Fly.io |
| Database | Supabase (PostgreSQL) |

---

## 🔑 Environment Variables

### Backend (Fly.io secrets)

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ | [console.groq.com](https://console.groq.com) |
| `SUPABASE_DB_URL` | ✅ | `postgresql://postgres:[pass]@db.[ref].supabase.co:5432/postgres` |
| `SECRET_KEY` | ✅ | `openssl rand -hex 32` |
| `CORS_ALLOWED_ORIGINS` | ✅ | Comma-separated frontend URLs |
| `RESEND_API_KEY` | optional | Email alerts via [resend.com](https://resend.com) |

### Frontend (Vercel env vars)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend URL: `https://llm-test-lab.fly.dev` |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key |

### GitHub Actions

| Name | Type | Description |
|---|---|---|
| `LLM_TEST_LAB_TOKEN` | Secret | API token from dashboard |
| `LLM_TEST_LAB_API_URL` | Variable | `https://llm-test-lab.fly.dev` |

> **Local dev:** If `SUPABASE_DB_URL` is not set, backend falls back to SQLite automatically.

---

## 📊 Roadmap

- [x] Multi-model eval engine
- [x] LLM-as-judge scoring (Groq)
- [x] RAG evaluation (faithfulness, context recall, answer relevancy, context precision)
- [x] Score history in Supabase
- [x] Auth + personal dashboards
- [x] A/B comparison
- [x] Score trend charts
- [x] CI/CD GitHub Action (`uses: seeshuraj/llm-test-lab@v1`)
- [x] Email alerts on score regression
- [x] Deployed on Fly.io (always-on)
- [ ] Stripe billing (Free / Pro / Teams)
- [ ] Slack / webhook notifications
- [ ] Drift detection alerts
- [ ] npm / PyPI SDK packages
- [ ] Live demo (no signup)

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
| Email | Resend |

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome — especially new eval metrics, scenario templates, and SDK improvements.

---

## 📄 License

[MIT](LICENSE) © 2026 [Seeshuraj Bhoopalan](https://github.com/seeshuraj)

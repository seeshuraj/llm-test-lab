# 🧪 LLM Test Lab

> Evaluate, score, and compare LLM outputs before your users do.

LLM Test Lab is an open-source evaluation platform for AI applications. Run your prompts across multiple models, score outputs automatically, track quality over time, and detect drift before it reaches production.

🌐 **Live Demo:** [llm-test-lab-psi.vercel.app](https://llm-test-lab-psi.vercel.app)  
📋 **Eval Engine:** [llm-test-lab-psi.vercel.app/eval](https://llm-test-lab-psi.vercel.app/eval)  
![CI](https://github.com/seeshuraj/llm-test-lab/actions/workflows/llm-eval.yml/badge.svg)

---

## ✨ Features

- **Multi-model comparison** — Run prompts across Llama 3.3 70B, Llama 3.1 8B, and more in parallel
- **Automated scoring** — Keyword + LLM-judge scoring against expected outputs
- **Latency tracking** — Per-model response time benchmarking
- **RAG evaluation** — Score Context Relevance, Faithfulness, and Answer Relevance via sentence-transformers embeddings
- **Score history** — Full run history persisted to Supabase (PostgreSQL)
- **A/B prompt comparison** — Compare two prompt variants side by side
- **CI/CD integration** — Auto-run evals on every push via GitHub Actions
- **Email alerts** — Notify when score drops below your threshold

---

## 🏗️ Architecture

```
llm-test-lab/
├── landing/            # Next.js landing page (Vercel)
├── apps/
│   ├── backend/        # FastAPI scoring engine + REST API (Railway / Render)
│   └── frontend/       # Main app: auth, dashboard, run history (Vercel)
├── packages/
│   ├── core-python/    # Shared Python models + judges
│   └── sdk-python/     # Python SDK (pip install coming soon)
├── cli/                # llm_eval.py — CI integration script
└── .github/workflows/  # CI: unit tests + LLM eval on every push
```

---

## 🚀 Getting Started

### Backend (FastAPI)
```bash
cd apps/backend
pip install -r requirements.txt
cp .env.example .env
# Fill in GROQ_API_KEY, SUPABASE_DB_URL (or leave blank for SQLite locally)
uvicorn app.main:app --reload
```

### Frontend (Next.js)
```bash
cd apps/frontend
npm install
cp .env.example .env.local
# Add NEXT_PUBLIC_API_URL pointing to your backend
npm run dev
```

### Run tests
```bash
pip install pytest
pytest apps/backend/tests/ -v
```

---

## 🔑 Environment Variables

### Backend (`apps/backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ | [console.groq.com](https://console.groq.com) |
| `SUPABASE_DB_URL` | ✅ prod | Supabase connection string (PostgreSQL) — e.g. `postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres` |
| `DATABASE_URL` | — | Overrides `SUPABASE_DB_URL` (Railway auto-injects this) |
| `CORS_ALLOWED_ORIGINS` | ✅ prod | Comma-separated allowed origins e.g. `https://your-app.vercel.app` |
| `RESEND_API_KEY` | optional | [resend.com](https://resend.com) — enables email score alerts |
| `FROM_EMAIL` | optional | Sender address for alerts (default: `onboarding@resend.dev`) |
| `APP_URL` | optional | Your frontend URL, used in alert email links |

> **Local dev:** If `SUPABASE_DB_URL` and `DATABASE_URL` are both unset, the backend falls back to SQLite (`llm_test_lab.db`). No setup needed.

### CI (GitHub Actions secrets + variables)

| Name | Type | Description |
|---|---|---|
| `LLM_TEST_LAB_TOKEN` | Secret | API token from your LLM Test Lab dashboard |
| `LLM_TEST_LAB_API_URL` | Variable | Your deployed backend URL, e.g. `https://llm-test-lab.onrender.com` |

---

## 📊 Roadmap

- [x] Multi-model eval engine
- [x] Latency benchmarking
- [x] LLM judge scoring (Groq)
- [x] RAG evaluation (faithfulness, context recall, answer relevancy)
- [x] Score history persisted to Supabase (PostgreSQL)
- [x] Auth + personal dashboards
- [x] API keys for CI/CD integration
- [x] CI/CD GitHub Actions integration
- [x] Email alerts on score regression
- [x] Unit tests for scoring logic
- [ ] Semantic scoring via sentence-transformers embeddings
- [ ] Stripe billing
- [ ] npm / PyPI SDK packages
- [ ] Slack / webhook notifications

---

## 🛠️ Tech Stack

| Layer | Tech |
|---|---|
| **Frontend** | Next.js, TypeScript, Tailwind CSS, Vercel |
| **Backend** | FastAPI, Python 3.11, SQLAlchemy (asyncpg) |
| **Database** | Supabase (PostgreSQL) — SQLite for local dev |
| **AI / Judges** | Groq (Llama 3.1, 3.3), sentence-transformers |
| **Auth** | JWT (python-jose + bcrypt) |
| **CI** | GitHub Actions |
| **Email** | Resend |

---

## 📢 CI Integration

Every push to `main` runs two jobs:

1. **Unit tests** — validates cosine similarity, JSON extraction, RagScores
2. **LLM eval** — runs `scenarios.yaml` against your deployed backend and fails if avg score < 0.6

See `.github/workflows/llm-eval.yml` and `cli/llm_eval.py`.

---

## 📄 License

MIT

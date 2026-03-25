
```markdown
# 🧪 LLM Test Lab

> Evaluate, score, and compare LLM outputs before your users do.

LLM Test Lab is an open-source evaluation platform for AI applications. Run your prompts across multiple models, score outputs automatically, track quality over time, and detect drift before it reaches production.

🌐 **Live Demo:** [llm-test-lab-psi.vercel.app](https://llm-test-lab-psi.vercel.app)
📋 **Eval Engine:** [llm-test-lab-psi.vercel.app/eval](https://llm-test-lab-psi.vercel.app/eval)

---

## ✨ Features

- **Multi-model comparison** — Run prompts across Llama 3.3 70B, Llama 3.1 8B, Gemini, and more in parallel
- **Automated scoring** — Keyword + semantic scoring against expected outputs
- **Latency tracking** — Per-model response time benchmarking
- **RAG evaluation** — Score Context Relevance, Faithfulness, and Answer Relevance
- **Score history** — Track prompt quality over time and detect drift
- **A/B prompt comparison** — Compare two prompt variants side by side
- **CI/CD integration** — Auto-run evals on every deployment *(coming soon)*

---

## 🏗️ Architecture

```
llm-test-lab/
├── landing/        # Next.js frontend + eval UI (Vercel)
├── apps/
│   ├── backend/    # FastAPI scoring engine (Python)
│   └── frontend/   # Main app with auth + dashboard
├── packages/       # Shared SDK (coming soon)
└── scenarios.yaml  # RAG test scenarios
```

---

## 🚀 Getting Started

### Frontend (Next.js)
```bash
cd landing
npm install
cp .env.example .env.local
# Add GROQ_API_KEY and GEMINI_API_KEY
npm run dev
```

### Backend (FastAPI)
```bash
pip install -r requirements.txt
uvicorn apps.backend.main:app --reload
```

---

## 🔑 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ | [console.groq.com](https://console.groq.com) |
| `GEMINI_API_KEY` | ✅ | [aistudio.google.com](https://aistudio.google.com) |
| `SUPABASE_URL` | 🔜 | Supabase project URL |
| `SUPABASE_ANON_KEY` | 🔜 | Supabase anon key |

---

## 📊 Roadmap

- [x] Multi-model eval engine
- [x] Latency benchmarking
- [x] Waitlist landing page
- [ ] Supabase score history
- [ ] Semantic scoring (embeddings)
- [ ] RAG eval (RAGAS metrics)
- [ ] Auth + personal dashboards
- [ ] API keys for CI/CD integration
- [ ] Stripe billing

---

## 🛠️ Tech Stack

**Frontend:** Next.js 16, TypeScript, Tailwind CSS, Vercel  
**Backend:** FastAPI, Python, RAGAS  
**AI:** Groq (Llama), Google Gemini, OpenAI  
**DB:** Supabase (PostgreSQL)  
**Auth:** Clerk  

---

## 📬 Stay Updated

Join the waitlist at [llm-test-lab-psi.vercel.app](https://llm-test-lab-psi.vercel.app) for early access.

---

## 📄 License

MIT
```
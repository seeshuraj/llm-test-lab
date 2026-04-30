# Contributing to LLM Test Lab

Thanks for your interest! LLM Test Lab is open-source and welcomes contributions of all kinds — bug fixes, new features, documentation improvements, and eval scenarios.

---

## Quick Start (Local Dev)

### Prerequisites
- Python 3.11+
- Node.js 18+
- A free [Groq API key](https://console.groq.com)
- A free [Supabase](https://supabase.com) project (or skip — SQLite works locally)

### 1. Clone and set up backend
```bash
git clone https://github.com/seeshuraj/llm-test-lab.git
cd llm-test-lab

cd apps/backend
pip install -r requirements.txt
cp .env.example .env
# Set GROQ_API_KEY in .env — that's the minimum needed
uvicorn app.main:app --reload --port 8000
```

### 2. Set up frontend
```bash
cd apps/frontend
npm install
cp .env.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

### 3. Run unit tests
```bash
pip install pytest pytest-asyncio
pytest apps/backend/tests/ -v
```

---

## Project Structure

```
llm-test-lab/
├── action.yml              # Reusable GitHub Action (uses: seeshuraj/llm-test-lab@v1)
├── landing/                # Next.js landing page
├── apps/
│   ├── backend/            # FastAPI eval engine + REST API
│   └── frontend/           # Main dashboard (auth, runs, compare, trends)
├── packages/
│   ├── core-python/        # Shared judges + scoring models
│   └── sdk-python/         # Python SDK
├── cli/
│   └── llm_eval.py         # CI script used by the GitHub Action
└── .github/workflows/      # CI: unit tests + LLM eval on push
```

---

## How to Contribute

### Bug fixes / features
1. Fork the repo and create a branch: `git checkout -b feat/my-feature`
2. Make your changes with tests where applicable
3. Run `pytest apps/backend/tests/ -v` — all tests must pass
4. Open a PR with a clear description of what and why

### Adding eval scenarios
Edit `scenarios.yaml` at the repo root. Each scenario needs:
```yaml
- id: my_scenario
  question: "What is the capital of France?"
  expected: "Paris"
```

### Good First Issues
Look for issues tagged [`good first issue`](https://github.com/seeshuraj/llm-test-lab/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) on GitHub.

---

## Code Style
- **Python**: PEP8, type hints where reasonable
- **TypeScript**: strict mode, no `any`
- **Commits**: use conventional commits — `feat:`, `fix:`, `docs:`, `chore:`

---

## Questions?

Open an issue or start a [discussion](https://github.com/seeshuraj/llm-test-lab/discussions). We respond fast.

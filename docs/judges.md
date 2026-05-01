# Judge Models

LLM Test Lab supports multiple LLM providers as evaluation judges. The judge model scores each scenario answer on correctness, faithfulness, and grounding.

## Supported Providers

| Model string | Provider | Speed | Best for |
|---|---|---|---|
| `llama-3.1-8b-instant` | Groq | ⚡ Fast | Default CI runs, high volume |
| `llama-3.3-70b-versatile` | Groq | 🎯 Accurate | High-stakes evals, final QA |
| `mixtral-8x7b-32768` | Groq | ⚡ Fast | Long-context scenarios |
| `gemma2-9b-it` | Groq | ⚡ Fast | Lightweight, open-weight |
| `claude-3-5-haiku` | Anthropic | ⚡ Fast | Best reasoning at low cost |
| `claude-3-5-sonnet` | Anthropic | 🎯 Accurate | Highest accuracy evals |
| `ollama:llama3` | Ollama (local) | 🏠 Local | Offline / private data |
| `ollama:mistral` | Ollama (local) | 🏠 Local | Offline / private data |

## Required API Keys

| Provider | Environment Variable | Get key |
|---|---|---|
| Groq | `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) |
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) |
| Ollama | *(none — local)* | [ollama.ai](https://ollama.ai) |

## Usage

### In the GitHub Action

```yaml
- uses: seeshuraj/llm-test-lab@v1
  with:
    model: claude-3-5-haiku      # or llama-3.1-8b-instant, ollama:llama3
    api-url: ${{ vars.LLM_TEST_LAB_API_URL }}
    token: ${{ secrets.LLM_TEST_LAB_TOKEN }}
    app-url: https://your-app.com/answer
    scenarios: scenarios.yaml
```

### In Python (direct)

```python
from llm_test_lab_core.judge_factory import get_judge

# Groq (default)
judge = get_judge("llama-3.1-8b-instant")

# Claude
judge = get_judge("claude-3-5-haiku")

# Ollama (local)
judge = get_judge("ollama:llama3")

# Score a single answer
result = await judge.score(
    question="What is the refund policy?",
    answer="Refunds are available within 30 days.",
    context_docs=["Customers may request refunds within 30 days of purchase."],
    rubric="Score correctness and faithfulness to the context.",
)
print(result)
# {'score': 0.95, 'reason': 'Answer is faithful and correct.', 'judge_model': 'claude:claude-3-5-haiku-20241022'}
```

### In the CLI

```bash
python cli/llm_eval.py \
  --scenarios scenarios.yaml \
  --model claude-3-5-haiku \
  --api-url https://llm-test-lab.fly.dev \
  --token YOUR_TOKEN
```

## How Scoring Works

Each scenario is scored across **4 RAG metrics**, each returning a float in `[0.0, 1.0]`:

| Metric | Method | Measures |
|---|---|---|
| `faithfulness` | LLM judge | Does the answer stay within the provided context? |
| `answer_relevancy` | Embedding similarity | Is the answer actually answering the question? |
| `context_recall` | Embedding similarity | Does the context contain enough to answer the question? |
| `context_precision` | LLM judge | Is the retrieved context focused and not noisy? |

The **composite score** (used for `fail-under` threshold) is the average of all four metrics.

## Choosing a Judge Model

- **Default / CI:** `llama-3.1-8b-instant` — fast, free tier on Groq, good enough for regressions
- **Critical evals / release gates:** `claude-3-5-sonnet` — highest accuracy, best at nuanced faithfulness
- **Private data / no internet:** `ollama:llama3` — fully local, no API keys needed
- **Balance of speed + accuracy:** `claude-3-5-haiku` — 2-3× more accurate than 8B Groq, still fast

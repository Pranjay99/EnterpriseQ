# Text-to-SQL LoRA Fine-Tuning

Fine-tune a small open LLM (**Qwen2.5-Coder-1.5B-Instruct**) with **QLoRA** to
generate SQLite queries for Enterprise Q's Text-to-SQL agent — replacing (or
backing up) the Gemini API call with a model we own.

## Why this exists

| Problem | How the LoRA helps |
|---|---|
| Gemini free tier = 15 req/min shared by all users | A self-served model has no external quota |
| Vendor lock-in for the core SQL skill | The adapter is ours; it can be hosted anywhere |
| Generic model → generic SQL | Trained on question→SQL pairs in *our exact prompt format* |

## Why LoRA / QLoRA (the resume version)

- **LoRA** freezes the base model and trains small low-rank adapter matrices
  (~0.5% of parameters) injected into the attention and MLP projections —
  full fine-tuning quality on this task at a fraction of the memory/compute.
- **QLoRA** loads the frozen base in 4-bit (NF4), so the whole run fits on a
  **free Colab T4 (16 GB)**. Trainable params ≈ 18M vs 1.5B total.
- The output artifact is a ~70 MB adapter, cheap to store, version, and host.

## The pipeline

```
finetuning/
├── README.md               ← you are here
├── train_lora_colab.ipynb  ← end-to-end training notebook (run on Colab, free T4)
└── evaluate_baseline.py    ← measures Gemini's SQL accuracy locally → baseline number
```

1. **Dataset** — [`b-mc2/sql-create-context`](https://huggingface.co/datasets/b-mc2/sql-create-context)
   (~78k natural-language question + `CREATE TABLE` context → SQL pairs).
   The notebook formats each example into the **same prompt template the backend
   uses at runtime** (`SQL_GENERATION_PROMPT`) — train/serve skew is the #1
   silent killer of fine-tunes. A held-out 200-example split is never trained on.
2. **Training** — Unsloth + TRL `SFTTrainer`, QLoRA config:
   | Hyperparameter | Value |
   |---|---|
   | Base model | `unsloth/Qwen2.5-Coder-1.5B-Instruct-bnb-4bit` |
   | LoRA rank r / alpha | 16 / 16 |
   | Target modules | q,k,v,o + gate,up,down projections |
   | Quantisation | 4-bit NF4 (QLoRA) |
   | Examples | 10,000 (1 epoch) |
   | Effective batch | 16 (2 × grad-accum 8) |
   | LR / schedule | 2e-4, linear, warmup 5% |
   | Wall clock on T4 | ~45–60 min |
3. **Evaluation** — normalized-SQL exact match on the held-out split, tuned vs
   un-tuned base, plus `evaluate_baseline.py` for the Gemini number →
   a three-way comparison table for the README/resume.
4. **Export** — adapter (`save_pretrained`), optional merge + **GGUF (Q4_K_M)**
   for llama.cpp/Ollama serving, optional push to Hugging Face Hub.

## How to run

1. Open `train_lora_colab.ipynb` in [Google Colab](https://colab.research.google.com)
   → Runtime → Change runtime type → **T4 GPU**.
2. Run all cells top to bottom. Nothing else to configure.
3. Download the `sql_lora_adapter/` folder (and optionally the GGUF) it produces.

## Serving the tuned model

Pick one when you're ready (the backend integration works with all of them):

| Option | Cost | Notes |
|---|---|---|
| **Ollama** on any machine with ≥4 GB RAM | free | `ollama create` from the GGUF; CPU is fine for a 1.5B Q4 model |
| **llama.cpp server** | free | `llama-server -m model.gguf --port 8080` — OpenAI-compatible out of the box |
| Together / Fireworks LoRA hosting | ~$ per token | upload the adapter, serverless |
| Temporary: Colab + cloudflared tunnel | free | good enough for a demo video |

## Backend integration

`backend/agents/sql_agent.py` reads three env vars. When set, **SQL generation**
goes to your tuned model via any OpenAI-compatible endpoint; answer
summarisation stays on Gemini. If the endpoint errors, it falls back to Gemini
automatically — the app never breaks because the fine-tune is down.

```env
SQL_LLM_ENDPOINT=http://localhost:8080/v1   # OpenAI-compatible base URL
SQL_LLM_MODEL=enterprise-q-sql-lora         # model name the server expects
SQL_LLM_API_KEY=                            # only if the host requires one
```

## Measuring the win

```bash
# 1. Baseline: how good is Gemini at the held-out set? (runs locally, needs GOOGLE_API_KEY)
python finetuning/evaluate_baseline.py --limit 100

# 2. Tuned + base numbers: printed by the eval cell in the Colab notebook
```

Record all three in this table when done:

| Model | Exact-match accuracy (held-out 200) |
|---|---|
| Qwen2.5-Coder-1.5B (no tuning) | _fill in_ |
| **+ our LoRA adapter** | _fill in_ |
| Gemini 2.5 Flash (baseline) | _fill in_ |

## Future work

- Mix in real logged question→SQL pairs from Enterprise Q usage (with feedback
  labels) and retrain — the dataset improves as the product is used.
- Execution-match evaluation (run both SQLs on seeded SQLite, compare result sets)
  — stricter and fairer than string match.
- DPO pass using 👍/👎 feedback once collected.

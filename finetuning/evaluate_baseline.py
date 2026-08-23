"""
evaluate_baseline.py — Measure Gemini 2.5 Flash's exact-match accuracy on the
SAME held-out split the Colab notebook uses, so the three-way comparison
(base model / +LoRA / Gemini) is apples-to-apples.

Usage (from repo root, needs GOOGLE_API_KEY in .env):
    python finetuning/evaluate_baseline.py --limit 100

Note: the free tier allows ~15 requests/min, so this sleeps between calls.
100 examples ≈ 7 minutes.

Requires: pip install datasets
"""

import argparse
import os
import re
import time

from dotenv import load_dotenv

load_dotenv()

# Must match the notebook exactly
N_TRAIN, N_EVAL = 10_000, 200
SEED = 42

PROMPT = """You are an expert SQL analyst. Given the database schema below,
write a single SQLite-compatible SELECT query that answers the user's question.

**Rules:**
- Output ONLY the SQL query — no explanation, no markdown.
- Use only columns and tables that exist in the schema.
- Never use DROP, DELETE, UPDATE, INSERT, ALTER, or CREATE.
- If the question is ambiguous, make a reasonable assumption.

Schema:
{schema}

User question: {question}

SQL Query:"""


def normalize_sql(s: str) -> str:
    s = re.sub(r"```(?:sql)?|```", "", s)
    return re.sub(r"\s+", " ", s).strip().rstrip(";").lower()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100,
                        help="How many held-out examples to score (max 200)")
    parser.add_argument("--sleep", type=float, default=4.5,
                        help="Seconds between API calls (free-tier rate limit)")
    args = parser.parse_args()

    from datasets import load_dataset  # deferred: not a backend dependency
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage

    raw = load_dataset("b-mc2/sql-create-context", split="train").shuffle(seed=SEED)
    eval_raw = raw.select(range(N_TRAIN, N_TRAIN + min(args.limit, N_EVAL)))

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        google_api_key=os.getenv("GOOGLE_API_KEY"),
    )

    hits = 0
    for i, ex in enumerate(eval_raw):
        prompt = PROMPT.format(schema=ex["context"], question=ex["question"])
        try:
            pred = llm.invoke([HumanMessage(content=prompt)]).content
        except Exception as e:
            print(f"[{i}] API error, skipping: {e}")
            time.sleep(args.sleep * 3)
            continue
        ok = normalize_sql(pred) == normalize_sql(ex["answer"])
        hits += ok
        print(f"[{i + 1}/{len(eval_raw)}] {'OK ' if ok else 'MISS'} running acc: {hits / (i + 1):.1%}")
        time.sleep(args.sleep)

    print(f"\nGemini 2.5 Flash baseline: {hits}/{len(eval_raw)} = {hits / len(eval_raw):.1%} exact match")


if __name__ == "__main__":
    main()

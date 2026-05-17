"""
data_agent.py — Core LLM orchestrator for EnterpriseQ AI (Level 1 Foundation).

Flow:
  1. Summarise the loaded DataFrame (shape, columns, sample rows, stats)
  2. Inject the summary + user question into the prompt
  3. Call Gemini 1.5 Flash (FREE tier) via LangChain ConversationChain
  4. Parse the LLM response for a chart hint  →  generate Plotly JSON if found
  5. Return { answer, chart_json }

Free tier limits (as of 2025):
  - 15 requests / minute
  - 1,000,000 tokens / minute
  - 1,500 requests / day
Get your free key at: https://aistudio.google.com/app/apikey
"""

import re
import os
from dotenv import load_dotenv

import pandas as pd
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.chains import ConversationChain
from langchain_core.prompts import PromptTemplate

from utils.memory_manager import get_memory
from utils.prompt_templates import DATA_ANALYSIS_PROMPT
from utils.chart_generator import generate_chart

load_dotenv()

# Initialise LLM once at module load — shared across requests.
# gemini-2.0-flash is FREE and fast — perfect for the Level 1 foundation.
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

# Chart-hint regex: matches "Chart: bar on Department vs AttritionRate"
_CHART_PATTERN = re.compile(
    r"Chart:\s*(bar|line|pie|scatter)\s+on\s+(.+?)\s+vs\s+(.+)",
    re.IGNORECASE,
)


def summarise_df(df: pd.DataFrame) -> str:
    """
    Build a compact text summary of a DataFrame to inject into the prompt.
    Keeps token usage low while giving the LLM enough context to answer well.
    """
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    summary_lines = [
        f"Shape: {df.shape[0]} rows × {df.shape[1]} columns",
        f"Columns: {list(df.columns)}",
        f"Numeric columns: {numeric_cols}",
        "",
        "Sample (first 3 rows):",
        df.head(3).to_markdown(index=False),
    ]
    if numeric_cols:
        summary_lines += [
            "",
            "Descriptive stats (numeric columns):",
            df[numeric_cols].describe().round(2).to_markdown(),
        ]
    return "\n".join(summary_lines)


def query_data(session_id: str, question: str, df: pd.DataFrame) -> dict:
    """
    Ask a question about a DataFrame.

    Args:
        session_id: Unique identifier for the user's session (memory key).
        question:   Natural-language question from the user.
        df:         The currently loaded DataFrame for this session.

    Returns:
        dict with keys:
          - 'answer'    (str)           — LLM text answer
          - 'chart_json' (str | None)   — Plotly JSON or None
    """
    memory = get_memory(session_id)
    data_summary = summarise_df(df)

    # Build the full prompt including data context
    full_question = DATA_ANALYSIS_PROMPT.format(data_summary=data_summary) + f"\n\nUser question: {question}"

    chain = ConversationChain(llm=llm, memory=memory, verbose=False)
    response: str = chain.predict(input=full_question)

    # Attempt to parse a chart hint from the LLM output
    chart_json = None
    match = _CHART_PATTERN.search(response)
    if match:
        chart_type = match.group(1)
        x_col = match.group(2).strip()
        y_col = match.group(3).strip()
        # Only generate a chart if "no chart" was not intended
        if "no chart" not in f"{chart_type} {x_col} {y_col}".lower():
            try:
                chart_json = generate_chart(df, chart_type, x_col, y_col)
            except Exception:
                chart_json = None  # Never crash the response over a chart failure

    return {"answer": response, "chart_json": chart_json}

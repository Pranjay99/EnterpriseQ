"""
sql_agent.py — Text-to-SQL agent for EnterpriseQ AI.

Flow:
  1. LLM receives the table schema + user question
  2. LLM generates a SELECT query
  3. Query executes against the in-memory SQLite database
  4. LLM summarises the raw results into a natural-language answer
  5. Optionally extracts a chart hint for Plotly visualisation
"""

import re
import os

import pandas as pd
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import HumanMessage

from utils.prompt_templates import SQL_GENERATION_PROMPT, SQL_ANSWER_PROMPT
from utils.chart_generator import generate_chart
from pipelines.sql_loader import get_table_schema

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)

# Chart-hint regex (same pattern as data_agent)
_CHART_PATTERN = re.compile(
    r"Chart:\s*(bar|line|pie|scatter)\s+on\s+(.+?)\s+vs\s+(.+)",
    re.IGNORECASE,
)

# Pattern to extract SQL from markdown code blocks or plain text
_SQL_BLOCK_PATTERN = re.compile(
    r"```(?:sql)?\s*\n?(.*?)\n?```",
    re.DOTALL | re.IGNORECASE,
)


def _extract_sql(llm_output: str) -> str:
    """Extract a clean SQL query from the LLM response."""
    # Try to pull SQL from a code block first
    match = _SQL_BLOCK_PATTERN.search(llm_output)
    if match:
        return match.group(1).strip()
    # Otherwise take the whole output, stripping common prefixes
    cleaned = llm_output.strip()
    for prefix in ("SQLQuery:", "SQL:", "Query:"):
        if cleaned.upper().startswith(prefix.upper()):
            cleaned = cleaned[len(prefix):].strip()
    return cleaned


def _validate_sql(sql: str) -> None:
    """Basic safety check — only allow SELECT statements."""
    first_keyword = sql.strip().split()[0].upper() if sql.strip() else ""
    if first_keyword not in ("SELECT", "WITH"):
        raise ValueError(
            f"Only SELECT queries are allowed. Got: {first_keyword}..."
        )


def query_sql(session_id: str, question: str, db: SQLDatabase, df: pd.DataFrame) -> dict:
    """
    Convert a natural-language question to SQL, execute it, and return
    a human-readable answer.

    Args:
        session_id: User session identifier.
        question:   Natural-language question.
        db:         LangChain SQLDatabase wrapping the session's SQLite.
        df:         Original DataFrame (used for chart generation).

    Returns:
        dict with keys: answer, chart_json, sql_query
    """
    schema = get_table_schema(db)

    # ── Step 1: Generate SQL ──────────────────────────────────────────────
    gen_prompt = SQL_GENERATION_PROMPT.format(
        table_schema=schema,
        question=question,
    )
    gen_response = llm.invoke([HumanMessage(content=gen_prompt)])
    sql_query = _extract_sql(gen_response.content)

    # ── Step 2: Validate & Execute ────────────────────────────────────────
    _validate_sql(sql_query)
    raw_result = db.run(sql_query)

    # ── Step 3: Generate natural-language answer ──────────────────────────
    answer_prompt = SQL_ANSWER_PROMPT.format(
        question=question,
        sql_query=sql_query,
        sql_result=raw_result,
    )
    answer_response = llm.invoke([HumanMessage(content=answer_prompt)])
    answer = answer_response.content

    # ── Step 4: Chart extraction ──────────────────────────────────────────
    chart_json = None
    match = _CHART_PATTERN.search(answer)
    if match:
        chart_type = match.group(1)
        x_col = match.group(2).strip()
        y_col = match.group(3).strip()
        if "no chart" not in f"{chart_type} {x_col} {y_col}".lower():
            try:
                chart_json = generate_chart(df, chart_type, x_col, y_col)
            except Exception:
                chart_json = None

    return {
        "answer": answer,
        "chart_json": chart_json,
        "sql_query": sql_query,
    }

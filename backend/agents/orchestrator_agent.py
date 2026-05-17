"""
orchestrator_agent.py — Classifies a query as MATH, REASON, or OTHER
using zero-cost keyword/regex heuristics (no LLM call).
"""

import re

# ── Keyword sets ──────────────────────────────────────────────────────────────

_MATH_KEYWORDS = {
    # Operators / operations
    "calculate", "compute", "solve", "evaluate", "simplify",
    "add", "subtract", "multiply", "divide", "sum", "product",
    "square root", "sqrt", "squared", "cubed", "power", "exponent",
    "log", "logarithm", "sine", "cosine", "tangent",
    # Conversion triggers
    "convert", "to miles", "to km", "to kg", "to pounds",
    "to fahrenheit", "to celsius", "to feet", "to meters", "to gallons",
    # Percentage triggers
    "percent", "percentage", "% of", "out of",
    # Math-y question words
    "how many", "how much", "total", "average", "mean", "median",
    "minimum", "maximum", "ratio", "proportion",
}

_REASON_KEYWORDS = {
    "if", "therefore", "deduce", "infer", "conclude",
    "logic", "logical", "puzzle", "riddle",
    "who is", "which one", "true or false", "is it possible",
    "can you prove", "prove that", "what follows", "what can we infer",
    "syllogism", "premise", "hypothesis", "what if",
    "all are", "none are", "some are",
}

# Regex: expression contains digits + an operator → likely math
_MATH_EXPR_RE = re.compile(r"\d[\d\s]*[+\-*/^%]\s*\d")


def classify_query(question: str) -> str:
    """
    Classify a question into one of: MATH | REASON | OTHER.
    Uses keyword/regex heuristics — no LLM call, no API quota used.
    """
    q = question.lower()

    # Numeric expression (e.g. "12 * 34", "sqrt(144)")
    if _MATH_EXPR_RE.search(q) or "sqrt(" in q or "log(" in q:
        return "MATH"

    for kw in _MATH_KEYWORDS:
        if kw in q:
            return "MATH"

    for kw in _REASON_KEYWORDS:
        if kw in q:
            return "REASON"

    return "OTHER"


def should_use_general_agent(question: str) -> bool:
    """
    Return True if the question should be routed to the GeneralAgent
    (i.e. it is classified as MATH or REASON).
    """
    return classify_query(question) in {"MATH", "REASON"}

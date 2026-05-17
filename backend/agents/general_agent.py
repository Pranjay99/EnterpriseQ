"""
general_agent.py — General-purpose agent with 4 tools:
  1. calculator       — safe math expression evaluator
  2. percentage       — percentage calculations
  3. unit_converter   — km/miles, kg/pounds, celsius/fahrenheit
  4. logical_reasoner — chain-of-thought reasoning via Gemini
"""

import ast
import math
import operator
import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)

# ── Safe math evaluator ───────────────────────────────────────────────────

_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_SAFE_FUNCS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "log": math.log,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "pi": math.pi,
    "e": math.e,
}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in _SAFE_FUNCS:
            return _SAFE_FUNCS[node.id]
        raise ValueError(f"Unknown name: {node.id}")
    if isinstance(node, ast.BinOp):
        op = type(node.op)
        if op not in _SAFE_OPS:
            raise ValueError(f"Unsupported operator: {op.__name__}")
        return _SAFE_OPS[op](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp):
        op = type(node.op)
        if op not in _SAFE_OPS:
            raise ValueError(f"Unsupported unary operator: {op.__name__}")
        return _SAFE_OPS[op](_safe_eval(node.operand))
    if isinstance(node, ast.Call):
        func = _safe_eval(node.func)
        args = [_safe_eval(a) for a in node.args]
        return func(*args)
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


# ── Tools ─────────────────────────────────────────────────────────────────

@tool
def calculator(expression: str) -> str:
    """
    Safely evaluate a mathematical expression.
    Supports: +, -, *, /, **, %, sqrt(), abs(), round(), log(), sin(), cos(), tan(), pi, e.
    Example: '2 ** 10 + sqrt(144)'
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _safe_eval(tree)
        return f"Result: {result}"
    except ZeroDivisionError:
        return "Error: Division by zero."
    except Exception as e:
        return f"Error evaluating expression: {e}"


@tool
def percentage(query: str) -> str:
    """
    Calculate percentages. Supports two formats:
    - 'X% of Y'      → calculates X percent of Y
    - 'X out of Y'   → calculates X as a percentage of Y
    Examples: '15% of 200', '45 out of 180'
    """
    import re

    q = query.strip().lower()

    # Pattern: X% of Y
    m = re.match(r"([\d.]+)\s*%\s*of\s*([\d.]+)", q)
    if m:
        x, y = float(m.group(1)), float(m.group(2))
        result = (x / 100) * y
        return f"{x}% of {y} = {result}"

    # Pattern: X out of Y
    m = re.match(r"([\d.]+)\s+out\s+of\s+([\d.]+)", q)
    if m:
        x, y = float(m.group(1)), float(m.group(2))
        if y == 0:
            return "Error: Cannot divide by zero."
        result = (x / y) * 100
        return f"{x} out of {y} = {result:.2f}%"

    return (
        "Could not parse percentage query. "
        "Use format '15% of 200' or '45 out of 180'."
    )


@tool
def unit_converter(query: str) -> str:
    """
    Convert between common units. Supported conversions:
    - Distance: km to miles, miles to km
    - Weight:   kg to pounds, pounds to kg
    - Temperature: celsius to fahrenheit, fahrenheit to celsius
    Example: '10 km to miles', '72 fahrenheit to celsius'
    """
    import re

    q = query.strip().lower()
    m = re.match(r"([\d.]+)\s+(.+?)\s+to\s+(.+)", q)
    if not m:
        return "Could not parse. Use format: '10 km to miles'"

    value = float(m.group(1))
    from_unit = m.group(2).strip().rstrip("s")  # normalise plural
    to_unit = m.group(3).strip().rstrip("s")

    conversions = {
        ("km", "mile"): lambda v: v * 0.621371,
        ("mile", "km"): lambda v: v * 1.60934,
        ("kg", "pound"): lambda v: v * 2.20462,
        ("pound", "kg"): lambda v: v / 2.20462,
        ("lb", "kg"): lambda v: v / 2.20462,
        ("kg", "lb"): lambda v: v * 2.20462,
        ("celsius", "fahrenheit"): lambda v: v * 9 / 5 + 32,
        ("fahrenheit", "celsius"): lambda v: (v - 32) * 5 / 9,
        ("c", "f"): lambda v: v * 9 / 5 + 32,
        ("f", "c"): lambda v: (v - 32) * 5 / 9,
        ("meter", "feet"): lambda v: v * 3.28084,
        ("feet", "meter"): lambda v: v / 3.28084,
        ("liter", "gallon"): lambda v: v * 0.264172,
        ("gallon", "liter"): lambda v: v / 0.264172,
    }

    fn = conversions.get((from_unit, to_unit))
    if fn:
        result = fn(value)
        return f"{value} {from_unit} = {result:.4f} {to_unit}"

    return (
        f"Unsupported conversion: {from_unit} to {to_unit}. "
        "Supported: km↔miles, kg↔pounds/lb, celsius↔fahrenheit, meters↔feet, liters↔gallons."
    )


@tool
def logical_reasoner(problem: str) -> str:
    """
    Solve logical, reasoning, or word problems using chain-of-thought thinking.
    Best for: logic puzzles, deduction, multi-step reasoning, what-if questions.
    Example: 'If Alice is taller than Bob and Bob is taller than Carol, who is shortest?'
    """
    prompt = f"""Think step by step to solve this problem.

Problem: {problem}

Instructions:
- Break down the problem into clear reasoning steps
- Label each step (Step 1, Step 2, etc.)
- State your final answer clearly at the end

Solution:"""
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


# ── Agent (LangChain v1 create_agent) ────────────────────────────────────

_TOOLS = [calculator, percentage, unit_converter, logical_reasoner]

_SYSTEM_PROMPT = (
    "You are EnterpriseQ AI's general-purpose assistant. "
    "Use the available tools to solve math problems, conversions, percentages, "
    "and logical reasoning questions accurately. "
    "Always show your work clearly."
)

_agent = create_agent(llm, _TOOLS, system_prompt=_SYSTEM_PROMPT)


def query_general(question: str) -> dict:
    """
    Run the general agent to answer math/reasoning questions.

    Returns:
        dict with keys: answer
    """
    result = _agent.invoke({"messages": [HumanMessage(content=question)]})
    messages = result.get("messages", [])
    answer = messages[-1].content if messages else "No answer returned."
    return {"answer": answer}

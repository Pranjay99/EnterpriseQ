"""
test_pipelines.py — Unit tests for data ingestion pipelines.

Run:
  pytest tests/test_pipelines.py -v
"""

import json
import os
import tempfile

import pandas as pd
import pytest

from pipelines.csv_loader import load_csv, load_excel
from pipelines.json_loader import load_json


# ── CSV loader ────────────────────────────────────────────────────────────────
def test_load_csv_basic():
    data = "name,age,department\nAlice,30,HR\nBob,25,Sales\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write(data)
        path = f.name
    try:
        df = load_csv(path)
        assert list(df.columns) == ["name", "age", "department"]
        assert len(df) == 2
        assert df.loc[0, "name"] == "Alice"
    finally:
        os.unlink(path)


# ── JSON loader ───────────────────────────────────────────────────────────────
def test_load_json_list():
    records = [{"id": 1, "value": 10}, {"id": 2, "value": 20}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(records, f)
        path = f.name
    try:
        df = load_json(path)
        assert len(df) == 2
        assert "id" in df.columns
    finally:
        os.unlink(path)


def test_load_json_single_object():
    record = {"product": "Widget", "price": 9.99}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(record, f)
        path = f.name
    try:
        df = load_json(path)
        assert len(df) == 1
        assert df.loc[0, "product"] == "Widget"
    finally:
        os.unlink(path)


# ── Chart generator ───────────────────────────────────────────────────────────
def test_chart_generator_bar():
    from utils.chart_generator import generate_chart
    df = pd.DataFrame({"Department": ["HR", "Sales"], "Attrition": [5, 12]})
    chart_json = generate_chart(df, "bar", "Department", "Attrition")
    assert chart_json is not None
    assert "data" in chart_json


def test_chart_generator_fallback_columns():
    """If column names don't match exactly, the generator should fall back gracefully."""
    from utils.chart_generator import generate_chart
    df = pd.DataFrame({"Department": ["HR", "Sales"], "Attrition": [5, 12]})
    # Pass lower-case column names — should still work via case-insensitive fallback
    chart_json = generate_chart(df, "bar", "department", "attrition")
    assert chart_json is not None

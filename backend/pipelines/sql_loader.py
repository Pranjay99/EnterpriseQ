"""
sql_loader.py — Convert pandas DataFrames into an in-memory SQLite database
wrapped by LangChain's SQLDatabase for Text-to-SQL queries.

A session can hold multiple tables (one per uploaded file), which lets the
SQL agent join across files.
"""

import re

import pandas as pd
from sqlalchemy import create_engine, text
from langchain_community.utilities import SQLDatabase


def filename_to_table(filename: str) -> str:
    """Derive a safe SQLite table name from an uploaded filename."""
    stem = filename.rsplit(".", 1)[0]
    name = re.sub(r"[^0-9a-zA-Z_]+", "_", stem).strip("_").lower() or "uploaded_data"
    if name[0].isdigit():
        name = f"t_{name}"
    return name


def add_df_to_sqlite(db: SQLDatabase | None, df: pd.DataFrame, table_name: str) -> SQLDatabase:
    """
    Add a DataFrame as a table to a session's in-memory SQLite database,
    creating the database on first use. Re-uploading a file with the same
    name replaces its table.

    Returns a SQLDatabase wrapper that exposes ALL tables in the session,
    so the SQL agent can join across uploaded files.
    """
    engine = db._engine if db is not None else create_engine("sqlite://", echo=False)
    df.to_sql(table_name, engine, index=False, if_exists="replace")
    return SQLDatabase(engine)


def df_to_sqlite(df: pd.DataFrame, table_name: str = "uploaded_data") -> SQLDatabase:
    """
    Load a DataFrame into an in-memory SQLite database and return a
    LangChain SQLDatabase wrapper.

    Args:
        df:         The DataFrame to load.
        table_name: Name of the table created in SQLite.

    Returns:
        A LangChain SQLDatabase instance connected to the in-memory DB.
    """
    engine = create_engine("sqlite://", echo=False)
    df.to_sql(table_name, engine, index=False, if_exists="replace")
    return SQLDatabase(engine, include_tables=[table_name])


def get_table_schema(db: SQLDatabase) -> str:
    """Return the CREATE TABLE DDL for all included tables."""
    return db.get_table_info()

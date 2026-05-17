"""
sql_loader.py — Convert a pandas DataFrame into an in-memory SQLite database
wrapped by LangChain's SQLDatabase for Text-to-SQL queries.
"""

import pandas as pd
from sqlalchemy import create_engine, text
from langchain_community.utilities import SQLDatabase


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

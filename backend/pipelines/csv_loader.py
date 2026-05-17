import pandas as pd


def load_csv(file_path: str) -> pd.DataFrame:
    """Load a CSV file into a DataFrame."""
    return pd.read_csv(file_path)


def load_excel(file_path: str) -> pd.DataFrame:
    """Load an Excel file (.xlsx / .xls) into a DataFrame."""
    return pd.read_excel(file_path, engine="openpyxl")

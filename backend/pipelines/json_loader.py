import json
import pandas as pd


def load_json(file_path: str) -> pd.DataFrame:
    """
    Load a JSON file into a DataFrame.
    Accepts either a list of records or a single object.
    """
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)
    return pd.DataFrame(data if isinstance(data, list) else [data])

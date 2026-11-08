"""EXTRACT - read the raw CSV."""
from pathlib import Path

import pandas as pd

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "data" / "student_performance.csv"


def extract_csv(path=DEFAULT_CSV):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python data/generate_data.py` or add your own CSV."
        )
    df = pd.read_csv(path, encoding="utf-8-sig", skipinitialspace=True)
    if df.empty:
        raise ValueError("The CSV file is empty.")
    return df

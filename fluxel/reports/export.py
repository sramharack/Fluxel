from __future__ import annotations

import json
from typing import Any

import pandas as pd


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def dict_to_json_bytes(data: dict[str, Any]) -> bytes:
    return json.dumps(data, indent=2, default=str).encode("utf-8")

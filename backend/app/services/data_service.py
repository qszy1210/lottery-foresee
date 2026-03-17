from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd

from app.config import settings
from app.domain.models import SsqDraw, DltDraw


def _parse_date(value: str) -> datetime.date:
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: {value}")


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    return df


def load_ssq_history() -> List[SsqDraw]:
    df = _load_csv(settings.ssq_csv_path)
    draws: List[SsqDraw] = []
    for _, row in df.iterrows():
        reds = [int(row[f"red{i}"]) for i in range(1, 7)]
        blue = int(row["blue1"])
        draws.append(
            SsqDraw(
                issue=str(row["issue"]),
                draw_date=_parse_date(str(row["date"])),
                reds=reds,
                blue=blue,
            )
        )
    return draws


def load_dlt_history() -> List[DltDraw]:
    df = _load_csv(settings.dlt_csv_path)
    draws: List[DltDraw] = []
    for _, row in df.iterrows():
        fronts = [int(row[f"front{i}"]) for i in range(1, 6)]
        backs = [int(row[f"back{i}"]) for i in range(1, 3)]
        draws.append(
            DltDraw(
                issue=str(row["issue"]),
                draw_date=_parse_date(str(row["date"])),
                fronts=fronts,
                backs=backs,
            )
        )
    return draws


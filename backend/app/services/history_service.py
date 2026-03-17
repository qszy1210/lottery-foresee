"""预测历史记录：追加与查询。"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

from app.config import DATA_DIR

SSQ_HISTORY_FILE = DATA_DIR / "prediction_history_ssq.json"
DLT_HISTORY_FILE = DATA_DIR / "prediction_history_dlt.json"
MAX_LIST = 50


def _ensure_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]", encoding="utf-8")


def _read_list(path: Path) -> List[dict]:
    _ensure_file(path)
    raw = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def _write_list(path: Path, data: List[dict]) -> None:
    _ensure_file(path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def append_ssq(params: dict, results: List[dict], *, target_issue: str | None = None, target_date: str | None = None) -> dict:
    record = {
        "id": str(uuid.uuid4()),
        "lottery_type": "ssq",
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "target_issue": target_issue,
        "target_date": target_date,
        "params": params,
        "results": results,
    }
    data = _read_list(SSQ_HISTORY_FILE)
    data.append(record)
    _write_list(SSQ_HISTORY_FILE, data[-500:])  # keep last 500
    return record


def append_dlt(params: dict, results: List[dict], *, target_issue: str | None = None, target_date: str | None = None) -> dict:
    record = {
        "id": str(uuid.uuid4()),
        "lottery_type": "dlt",
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "target_issue": target_issue,
        "target_date": target_date,
        "params": params,
        "results": results,
    }
    data = _read_list(DLT_HISTORY_FILE)
    data.append(record)
    _write_list(DLT_HISTORY_FILE, data[-500:])
    return record


def list_ssq(limit: int = MAX_LIST) -> List[dict]:
    data = _read_list(SSQ_HISTORY_FILE)
    return list(reversed(data[-limit:]))


def list_dlt(limit: int = MAX_LIST) -> List[dict]:
    data = _read_list(DLT_HISTORY_FILE)
    return list(reversed(data[-limit:]))

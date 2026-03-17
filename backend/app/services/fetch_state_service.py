from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Literal, Optional

from app.config import DATA_DIR

LotteryType = Literal["ssq", "dlt"]

STATE_FILE = DATA_DIR / "fetch_state.json"


def _ensure() -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not STATE_FILE.exists():
        STATE_FILE.write_text("{}", encoding="utf-8")


def _read() -> dict:
    _ensure()
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write(state: dict) -> None:
    _ensure()
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_last_fetch_at(lottery: LotteryType) -> Optional[datetime]:
    state = _read()
    raw = (state.get(lottery) or {}).get("last_fetch_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def set_last_fetch_at(lottery: LotteryType, ts: datetime) -> None:
    state = _read()
    if lottery not in state:
        state[lottery] = {}
    state[lottery]["last_fetch_at"] = ts.astimezone(timezone.utc).isoformat()
    _write(state)


def should_fetch(lottery: LotteryType, *, min_interval_hours: int = 6) -> bool:
    last = get_last_fetch_at(lottery)
    if not last:
        return True
    now = datetime.now(tz=timezone.utc)
    delta_hours = (now - last).total_seconds() / 3600.0
    # 规则：超过 min_interval_hours 或跨日就拉取一次
    if delta_hours >= float(min_interval_hours):
        return True
    if last.date() < now.date():
        return True
    return False


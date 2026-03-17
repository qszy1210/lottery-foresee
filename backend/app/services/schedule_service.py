from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal, Optional

from app.services.data_service import load_ssq_history, load_dlt_history

LotteryType = Literal["ssq", "dlt"]


@dataclass(frozen=True)
class NextIssueInfo:
    lottery_type: LotteryType
    issue: str
    draw_date: date


def _next_draw_date(lottery_type: LotteryType, today: Optional[date] = None) -> date:
    today = today or date.today()
    # Python weekday: Mon=0 ... Sun=6
    if lottery_type == "ssq":
        draw_days = {1, 3, 6}  # Tue, Thu, Sun
    else:
        draw_days = {0, 2, 5}  # Mon, Wed, Sat

    d = today
    # 如果今天正好是开奖日，也视为“下一期”在今天（通常开奖日在晚间）
    for _ in range(14):
        if d.weekday() in draw_days:
            return d
        d = d + timedelta(days=1)
    return d


def _increment_issue(last_issue: str) -> str:
    s = str(last_issue).strip()
    width = len(s)
    try:
        n = int(s)
        return str(n + 1).zfill(width)
    except Exception:
        # fallback: 不可解析则直接返回原值（后续可完善更复杂的规则）
        return s


def get_next_issue_info(lottery_type: LotteryType) -> NextIssueInfo:
    if lottery_type == "ssq":
        draws = load_ssq_history()
    else:
        draws = load_dlt_history()
    if not draws:
        # 没有历史数据时用占位
        return NextIssueInfo(lottery_type=lottery_type, issue="UNKNOWN", draw_date=_next_draw_date(lottery_type))

    # 取历史最大期号并加 1
    last = max(draws, key=lambda x: int(x.issue) if str(x.issue).isdigit() else -1)
    next_issue = _increment_issue(last.issue)
    return NextIssueInfo(lottery_type=lottery_type, issue=next_issue, draw_date=_next_draw_date(lottery_type))


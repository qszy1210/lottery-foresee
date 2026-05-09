"""通知脚本（按周几判断彩种）的测试。"""
from __future__ import annotations

from datetime import date

from app.scripts.notify_predictions import _decide_lotteries


class TestDecideLotteries:
    """根据日期判断今天该推送哪些彩种。"""

    # 2026-03-23 = 周一 (DLT)
    # 2026-03-24 = 周二 (SSQ)
    # 2026-03-25 = 周三 (DLT)
    # 2026-03-26 = 周四 (SSQ)
    # 2026-03-27 = 周五 (无)
    # 2026-03-28 = 周六 (DLT)
    # 2026-03-29 = 周日 (SSQ)

    def test_monday_returns_dlt(self):
        assert _decide_lotteries(date(2026, 3, 23)) == ["dlt"]

    def test_tuesday_returns_ssq(self):
        assert _decide_lotteries(date(2026, 3, 24)) == ["ssq"]

    def test_wednesday_returns_dlt(self):
        assert _decide_lotteries(date(2026, 3, 25)) == ["dlt"]

    def test_thursday_returns_ssq(self):
        assert _decide_lotteries(date(2026, 3, 26)) == ["ssq"]

    def test_friday_returns_empty(self):
        assert _decide_lotteries(date(2026, 3, 27)) == []

    def test_saturday_returns_dlt(self):
        assert _decide_lotteries(date(2026, 3, 28)) == ["dlt"]

    def test_sunday_returns_ssq(self):
        assert _decide_lotteries(date(2026, 3, 29)) == ["ssq"]

    def test_override_ssq(self):
        # 周五本无开奖，手动指定也能返回
        assert _decide_lotteries(date(2026, 3, 27), override="ssq") == ["ssq"]

    def test_override_dlt(self):
        assert _decide_lotteries(date(2026, 3, 27), override="dlt") == ["dlt"]

    def test_override_both(self):
        assert _decide_lotteries(date(2026, 3, 27), override="both") == ["ssq", "dlt"]

    def test_override_auto_same_as_default(self):
        assert _decide_lotteries(date(2026, 3, 24), override="auto") == ["ssq"]

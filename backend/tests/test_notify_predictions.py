"""通知脚本（彩种选择策略）的测试。"""
from __future__ import annotations

from datetime import date

from app.scripts.notify_predictions import _decide_lotteries


# 2026-03-23 = 周一 (DLT)
# 2026-03-24 = 周二 (SSQ)
# 2026-03-25 = 周三 (DLT)
# 2026-03-26 = 周四 (SSQ)
# 2026-03-27 = 周五 (无)
# 2026-03-28 = 周六 (DLT)
# 2026-03-29 = 周日 (SSQ)


class TestAutoMode:
    """auto 默认每天都推送双色球 + 大乐透。"""

    def test_auto_monday_returns_both(self):
        assert _decide_lotteries(date(2026, 3, 23)) == ["ssq", "dlt"]

    def test_auto_friday_returns_both(self):
        # 即使周五本无开奖，auto 也会推两个彩种（提前公布）
        assert _decide_lotteries(date(2026, 3, 27)) == ["ssq", "dlt"]

    def test_auto_explicit(self):
        assert _decide_lotteries(date(2026, 3, 28), override="auto") == ["ssq", "dlt"]

    def test_default_is_auto(self):
        # 任意一天，默认都返回 ssq + dlt
        for day in range(23, 30):
            assert _decide_lotteries(date(2026, 3, day)) == ["ssq", "dlt"]


class TestExplicitOverrides:
    """明确指定 ssq / dlt / both 时按指定返回。"""

    def test_override_ssq(self):
        assert _decide_lotteries(date(2026, 3, 27), override="ssq") == ["ssq"]

    def test_override_dlt(self):
        assert _decide_lotteries(date(2026, 3, 27), override="dlt") == ["dlt"]

    def test_override_both(self):
        assert _decide_lotteries(date(2026, 3, 27), override="both") == ["ssq", "dlt"]


class TestDrawDayMode:
    """draw_day 模式：只推当天开奖的彩种（旧版 auto 行为）。"""

    def test_monday_returns_dlt(self):
        assert _decide_lotteries(date(2026, 3, 23), override="draw_day") == ["dlt"]

    def test_tuesday_returns_ssq(self):
        assert _decide_lotteries(date(2026, 3, 24), override="draw_day") == ["ssq"]

    def test_wednesday_returns_dlt(self):
        assert _decide_lotteries(date(2026, 3, 25), override="draw_day") == ["dlt"]

    def test_thursday_returns_ssq(self):
        assert _decide_lotteries(date(2026, 3, 26), override="draw_day") == ["ssq"]

    def test_friday_returns_empty(self):
        assert _decide_lotteries(date(2026, 3, 27), override="draw_day") == []

    def test_saturday_returns_dlt(self):
        assert _decide_lotteries(date(2026, 3, 28), override="draw_day") == ["dlt"]

    def test_sunday_returns_ssq(self):
        assert _decide_lotteries(date(2026, 3, 29), override="draw_day") == ["ssq"]

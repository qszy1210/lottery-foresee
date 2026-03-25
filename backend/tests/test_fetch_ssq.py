"""双色球数据拉取模块的测试。

覆盖场景：
- bundled CSV 加载
- runtime CSV 加载
- 记录合并与去重
- CWL API 解析
- 500.com HTML 解析
- 多源容错降级
- 增量更新逻辑
"""
from __future__ import annotations

import csv
import json
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests as requests_lib

from app.scripts.fetch_ssq import (
    _read_csv,
    _write_csv,
    _merge_records,
    _max_issue,
    _fetch_from_cwl,
    _fetch_from_500com,
    fetch_ssq_history,
    FIELDNAMES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_csv(tmp_path: Path):
    """创建临时 CSV 并返回路径。"""
    def _make(rows: list[dict[str, str]], name: str = "test.csv") -> Path:
        p = tmp_path / name
        with p.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
        return p
    return _make


SAMPLE_ROWS = [
    {"issue": "2024001", "date": "2024-01-01", "red1": "01", "red2": "05",
     "red3": "10", "red4": "15", "red5": "20", "red6": "25", "blue1": "07"},
    {"issue": "2024002", "date": "2024-01-04", "red1": "02", "red2": "08",
     "red3": "12", "red4": "18", "red5": "22", "red6": "30", "blue1": "03"},
]

SAMPLE_ROW_NEW = {
    "issue": "2024003", "date": "2024-01-07", "red1": "03", "red2": "09",
    "red3": "14", "red4": "19", "red5": "24", "red6": "31", "blue1": "11",
}


# ---------------------------------------------------------------------------
# CSV 读写
# ---------------------------------------------------------------------------

class TestCsvIO:
    def test_read_csv(self, tmp_csv):
        path = tmp_csv(SAMPLE_ROWS)
        rows = _read_csv(path)
        assert len(rows) == 2
        assert rows[0]["issue"] == "2024001"
        assert rows[1]["blue1"] == "03"

    def test_read_csv_missing_file(self, tmp_path: Path):
        assert _read_csv(tmp_path / "nonexistent.csv") == []

    def test_write_csv(self, tmp_path: Path):
        out = tmp_path / "out.csv"
        _write_csv(out, SAMPLE_ROWS)
        assert out.exists()
        rows = _read_csv(out)
        assert len(rows) == 2
        assert rows[0]["issue"] == "2024001"

    def test_write_csv_creates_parent_dir(self, tmp_path: Path):
        out = tmp_path / "sub" / "deep" / "out.csv"
        _write_csv(out, SAMPLE_ROWS)
        assert out.exists()


# ---------------------------------------------------------------------------
# 合并与去重
# ---------------------------------------------------------------------------

class TestMerge:
    def test_merge_dedup(self):
        a = [SAMPLE_ROWS[0]]
        b = [SAMPLE_ROWS[0], SAMPLE_ROWS[1]]
        result = _merge_records(a, b)
        assert len(result) == 2

    def test_merge_sort_order(self):
        reversed_rows = list(reversed(SAMPLE_ROWS))
        result = _merge_records(reversed_rows)
        assert result[0]["issue"] < result[1]["issue"]

    def test_merge_later_overrides(self):
        old = [{"issue": "2024001", "date": "2024-01-01", "red1": "01", "red2": "05",
                "red3": "10", "red4": "15", "red5": "20", "red6": "25", "blue1": "07"}]
        new = [{"issue": "2024001", "date": "2024-01-01", "red1": "99", "red2": "05",
                "red3": "10", "red4": "15", "red5": "20", "red6": "25", "blue1": "07"}]
        result = _merge_records(old, new)
        assert result[0]["red1"] == "99"

    def test_merge_empty(self):
        assert _merge_records([], []) == []

    def test_max_issue(self):
        assert _max_issue(SAMPLE_ROWS) == "2024002"
        assert _max_issue([]) is None


# ---------------------------------------------------------------------------
# CWL API 解析
# ---------------------------------------------------------------------------

class TestCwlApi:
    def _make_cwl_response(self, items: list[dict]) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = items
        resp.raise_for_status = MagicMock()
        return resp

    def test_parse_cwl_response(self):
        api_data = [
            {"code": "2024003", "date": "2024-01-07(日)",
             "red": "03,09,14,19,24,31", "blue": "11"},
            {"code": "2024002", "date": "2024-01-04(四)",
             "red": "02,08,12,18,22,30", "blue": "03"},
        ]
        with patch("app.scripts.fetch_ssq.requests.get") as mock_get:
            mock_get.return_value = self._make_cwl_response(api_data)
            result = _fetch_from_cwl(after_issue="2024001")

        assert len(result) == 2
        assert result[0]["issue"] == "2024003"
        assert result[0]["date"] == "2024-01-07"
        assert result[0]["red1"] == "03"
        assert result[0]["blue1"] == "11"

    def test_cwl_incremental_stops_at_known_issue(self):
        api_data = [
            {"code": "2024003", "date": "2024-01-07(日)",
             "red": "03,09,14,19,24,31", "blue": "11"},
            {"code": "2024002", "date": "2024-01-04(四)",
             "red": "02,08,12,18,22,30", "blue": "03"},
            {"code": "2024001", "date": "2024-01-01(一)",
             "red": "01,05,10,15,20,25", "blue": "07"},
        ]
        with patch("app.scripts.fetch_ssq.requests.get") as mock_get:
            mock_get.return_value = self._make_cwl_response(api_data)
            result = _fetch_from_cwl(after_issue="2024002")

        assert len(result) == 1
        assert result[0]["issue"] == "2024003"

    def test_cwl_network_error_propagates(self):
        with patch("app.scripts.fetch_ssq.requests.get") as mock_get:
            mock_get.side_effect = requests_lib.ConnectionError("timeout")
            with pytest.raises(requests_lib.ConnectionError):
                _fetch_from_cwl()


# ---------------------------------------------------------------------------
# 500.com HTML 解析
# ---------------------------------------------------------------------------

_500COM_HTML = textwrap.dedent("""\
    <html><body>
    <table id="tablelist">
    <tr><td>期号</td><td colspan="6">红球</td><td>蓝球</td>
        <td></td><td></td><td></td><td></td><td></td><td></td><td></td><td>日期</td></tr>
    <tr>
      <td>26032</td>
      <td>01</td><td>03</td><td>11</td><td>18</td><td>31</td><td>33</td>
      <td>02</td>
      <td></td><td>2278784926</td><td>6</td><td>7330318</td>
      <td>120</td><td>466063</td><td>392702390</td>
      <td>2026-03-24</td>
    </tr>
    <tr>
      <td>26031</td>
      <td>03</td><td>10</td><td>12</td><td>13</td><td>18</td><td>33</td>
      <td>08</td>
      <td></td><td>2200000000</td><td>5</td><td>8000000</td>
      <td>100</td><td>500000</td><td>300000000</td>
      <td>2026-03-22</td>
    </tr>
    </table>
    </body></html>
""")


class Test500com:
    def _mock_response(self, html: str) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.text = html
        resp.encoding = "utf-8"
        resp.raise_for_status = MagicMock()
        return resp

    def test_parse_500com_html(self):
        with patch("app.scripts.fetch_ssq.requests.get") as mock_get:
            mock_get.return_value = self._mock_response(_500COM_HTML)
            result = _fetch_from_500com()

        assert len(result) == 2
        assert result[0]["issue"] == "2026032"
        assert result[0]["red1"] == "01"
        assert result[0]["blue1"] == "02"
        assert result[0]["date"] == "2026-03-24"

    def test_500com_incremental(self):
        with patch("app.scripts.fetch_ssq.requests.get") as mock_get:
            mock_get.return_value = self._mock_response(_500COM_HTML)
            result = _fetch_from_500com(after_issue="2026031")

        assert len(result) == 1
        assert result[0]["issue"] == "2026032"

    def test_500com_normalizes_5digit_issue(self):
        html_5digit = _500COM_HTML.replace("26032", "03001").replace("26031", "03002")
        with patch("app.scripts.fetch_ssq.requests.get") as mock_get:
            mock_get.return_value = self._mock_response(html_5digit)
            result = _fetch_from_500com()

        for r in result:
            assert len(r["issue"]) == 7
            assert r["issue"].startswith("20")


# ---------------------------------------------------------------------------
# 端到端：fetch_ssq_history
# ---------------------------------------------------------------------------

class TestFetchSsqHistory:
    def test_bundled_only_no_network(self, tmp_path: Path, tmp_csv):
        """所有在线源失败时，bundled 数据仍可用。"""
        bundled_path = tmp_csv(SAMPLE_ROWS, "bundled.csv")
        runtime_path = tmp_path / "runtime.csv"

        with patch("app.scripts.fetch_ssq.BUNDLED_CSV", bundled_path), \
             patch("app.scripts.fetch_ssq.RUNTIME_CSV", runtime_path), \
             patch("app.scripts.fetch_ssq._SOURCES", [
                 ("mock_source", MagicMock(side_effect=Exception("network down"))),
             ]):
            fetch_ssq_history()

        rows = _read_csv(runtime_path)
        assert len(rows) == 2

    def test_incremental_update(self, tmp_path: Path, tmp_csv):
        """增量更新：在线源返回新数据后合并到 runtime。"""
        bundled_path = tmp_csv(SAMPLE_ROWS, "bundled.csv")
        runtime_path = tmp_path / "runtime.csv"

        def fake_fetch(after_issue=None):
            if after_issue == "2024002":
                return [SAMPLE_ROW_NEW]
            return SAMPLE_ROWS + [SAMPLE_ROW_NEW]

        with patch("app.scripts.fetch_ssq.BUNDLED_CSV", bundled_path), \
             patch("app.scripts.fetch_ssq.RUNTIME_CSV", runtime_path), \
             patch("app.scripts.fetch_ssq._SOURCES", [
                 ("mock", fake_fetch),
             ]):
            fetch_ssq_history()

        rows = _read_csv(runtime_path)
        assert len(rows) == 3
        assert rows[-1]["issue"] == "2024003"

    def test_no_local_no_network_raises(self, tmp_path: Path):
        """本地无数据且网络全失败时应抛出异常。"""
        bundled_path = tmp_path / "nonexistent_bundled.csv"
        runtime_path = tmp_path / "nonexistent_runtime.csv"

        with patch("app.scripts.fetch_ssq.BUNDLED_CSV", bundled_path), \
             patch("app.scripts.fetch_ssq.RUNTIME_CSV", runtime_path), \
             patch("app.scripts.fetch_ssq._SOURCES", [
                 ("mock_source", MagicMock(side_effect=Exception("fail"))),
             ]):
            with pytest.raises(RuntimeError, match="所有数据源均不可用"):
                fetch_ssq_history()

    def test_fallback_to_second_source(self, tmp_path: Path, tmp_csv):
        """第一个源失败后切换到第二个源。"""
        bundled_path = tmp_csv(SAMPLE_ROWS, "bundled.csv")
        runtime_path = tmp_path / "runtime.csv"

        def good_source(after_issue=None):
            return [SAMPLE_ROW_NEW]

        with patch("app.scripts.fetch_ssq.BUNDLED_CSV", bundled_path), \
             patch("app.scripts.fetch_ssq.RUNTIME_CSV", runtime_path), \
             patch("app.scripts.fetch_ssq._SOURCES", [
                 ("bad", MagicMock(side_effect=Exception("fail"))),
                 ("good", good_source),
             ]):
            fetch_ssq_history()

        rows = _read_csv(runtime_path)
        assert len(rows) == 3

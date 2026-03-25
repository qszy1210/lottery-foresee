"""大乐透数据拉取模块的测试。"""
from __future__ import annotations

import csv
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.scripts.fetch_dlt import (
    _read_csv,
    _write_csv,
    _merge_records,
    _max_issue,
    _fetch_from_500com,
    fetch_dlt_history,
    FIELDNAMES,
)


@pytest.fixture
def tmp_csv(tmp_path: Path):
    def _make(rows: list[dict[str, str]], name: str = "test.csv") -> Path:
        p = tmp_path / name
        with p.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
        return p
    return _make


DLT_ROWS = [
    {"issue": "2024001", "date": "2024-01-01",
     "front1": "01", "front2": "08", "front3": "15", "front4": "22", "front5": "29",
     "back1": "03", "back2": "10"},
    {"issue": "2024002", "date": "2024-01-03",
     "front1": "05", "front2": "12", "front3": "18", "front4": "25", "front5": "33",
     "back1": "06", "back2": "11"},
]

DLT_ROW_NEW = {
    "issue": "2024003", "date": "2024-01-06",
    "front1": "02", "front2": "10", "front3": "20", "front4": "28", "front5": "35",
    "back1": "01", "back2": "09",
}


# ---------------------------------------------------------------------------
# CSV 与合并
# ---------------------------------------------------------------------------

class TestCsvAndMerge:
    def test_read_write_roundtrip(self, tmp_path: Path):
        out = tmp_path / "dlt.csv"
        _write_csv(out, DLT_ROWS)
        rows = _read_csv(out)
        assert len(rows) == 2
        assert rows[0]["front1"] == "01"

    def test_merge_dedup_and_sort(self):
        result = _merge_records(
            [DLT_ROWS[1], DLT_ROWS[0]],
            [DLT_ROWS[0]],
        )
        assert len(result) == 2
        assert result[0]["issue"] == "2024001"

    def test_max_issue(self):
        assert _max_issue(DLT_ROWS) == "2024002"
        assert _max_issue([]) is None


# ---------------------------------------------------------------------------
# 500.com HTML 解析
# ---------------------------------------------------------------------------

_DLT_HTML = textwrap.dedent("""\
    <html><body>
    <table id="tablelist">
    <tr><td>期号</td><td colspan="5">前区</td><td colspan="2">后区</td>
        <td></td><td></td><td></td><td></td><td></td><td></td><td>日期</td></tr>
    <tr>
      <td>26030</td>
      <td>02</td><td>13</td><td>22</td><td>28</td><td>34</td>
      <td>05</td><td>12</td>
      <td>801741817</td><td>8</td><td>7605701</td>
      <td>97</td><td>179985</td><td>316922568</td>
      <td>2026-03-23</td>
    </tr>
    <tr>
      <td>26029</td>
      <td>03</td><td>05</td><td>17</td><td>33</td><td>35</td>
      <td>05</td><td>07</td>
      <td>700000000</td><td>6</td><td>7000000</td>
      <td>80</td><td>200000</td><td>300000000</td>
      <td>2026-03-21</td>
    </tr>
    </table>
    </body></html>
""")


class Test500comDlt:
    def _mock_response(self, html: str) -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.text = html
        resp.encoding = "utf-8"
        resp.raise_for_status = MagicMock()
        return resp

    def test_parse_dlt_html(self):
        with patch("app.scripts.fetch_dlt.requests.get") as mock_get:
            mock_get.return_value = self._mock_response(_DLT_HTML)
            result = _fetch_from_500com()

        assert len(result) == 2
        assert result[0]["issue"] == "2026030"
        assert result[0]["front1"] == "02"
        assert result[0]["back2"] == "12"
        assert result[0]["date"] == "2026-03-23"

    def test_incremental_filter(self):
        with patch("app.scripts.fetch_dlt.requests.get") as mock_get:
            mock_get.return_value = self._mock_response(_DLT_HTML)
            result = _fetch_from_500com(after_issue="2026029")

        assert len(result) == 1
        assert result[0]["issue"] == "2026030"


# ---------------------------------------------------------------------------
# 端到端
# ---------------------------------------------------------------------------

class TestFetchDltHistory:
    def test_bundled_only_no_network(self, tmp_path: Path, tmp_csv):
        bundled_path = tmp_csv(DLT_ROWS, "bundled.csv")
        runtime_path = tmp_path / "runtime.csv"

        with patch("app.scripts.fetch_dlt.BUNDLED_CSV", bundled_path), \
             patch("app.scripts.fetch_dlt.RUNTIME_CSV", runtime_path), \
             patch("app.scripts.fetch_dlt._SOURCES", [
                 ("mock", MagicMock(side_effect=Exception("down"))),
             ]):
            fetch_dlt_history()

        rows = _read_csv(runtime_path)
        assert len(rows) == 2

    def test_incremental_update(self, tmp_path: Path, tmp_csv):
        bundled_path = tmp_csv(DLT_ROWS, "bundled.csv")
        runtime_path = tmp_path / "runtime.csv"

        def fake_fetch(after_issue=None):
            return [DLT_ROW_NEW]

        with patch("app.scripts.fetch_dlt.BUNDLED_CSV", bundled_path), \
             patch("app.scripts.fetch_dlt.RUNTIME_CSV", runtime_path), \
             patch("app.scripts.fetch_dlt._SOURCES", [("mock", fake_fetch)]):
            fetch_dlt_history()

        rows = _read_csv(runtime_path)
        assert len(rows) == 3
        assert rows[-1]["issue"] == "2024003"

    def test_no_data_no_network_raises(self, tmp_path: Path):
        with patch("app.scripts.fetch_dlt.BUNDLED_CSV", tmp_path / "no.csv"), \
             patch("app.scripts.fetch_dlt.RUNTIME_CSV", tmp_path / "no2.csv"), \
             patch("app.scripts.fetch_dlt._SOURCES", [
                 ("mock", MagicMock(side_effect=Exception("fail"))),
             ]):
            with pytest.raises(RuntimeError, match="所有数据源均不可用"):
                fetch_dlt_history()

    def test_fallback_source(self, tmp_path: Path, tmp_csv):
        bundled_path = tmp_csv(DLT_ROWS, "bundled.csv")
        runtime_path = tmp_path / "runtime.csv"

        with patch("app.scripts.fetch_dlt.BUNDLED_CSV", bundled_path), \
             patch("app.scripts.fetch_dlt.RUNTIME_CSV", runtime_path), \
             patch("app.scripts.fetch_dlt._SOURCES", [
                 ("bad", MagicMock(side_effect=Exception("fail"))),
                 ("good", lambda after_issue=None: [DLT_ROW_NEW]),
             ]):
            fetch_dlt_history()

        rows = _read_csv(runtime_path)
        assert len(rows) == 3

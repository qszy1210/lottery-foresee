"""大乐透数据拉取：本地优先 + 增量更新 + 多源容错。

策略与 fetch_ssq 一致：bundled → runtime → 在线增量 → 合并写回。
"""
from __future__ import annotations

import csv
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from app.config import DATA_DIR

logger = logging.getLogger(__name__)

BUNDLED_CSV = Path(__file__).resolve().parent.parent / "data" / "dlt_history_bundled.csv"
RUNTIME_CSV = DATA_DIR / "dlt_history.csv"
FIELDNAMES = ["issue", "date", "front1", "front2", "front3", "front4", "front5", "back1", "back2"]

_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def _read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, records: List[Dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)


def _merge_records(*sources: List[Dict[str, str]]) -> List[Dict[str, str]]:
    merged: Dict[str, Dict[str, str]] = {}
    for records in sources:
        for r in records:
            merged[r["issue"]] = r
    return sorted(merged.values(), key=lambda r: r["issue"])


def _max_issue(records: List[Dict[str, str]]) -> Optional[str]:
    if not records:
        return None
    return max(r["issue"] for r in records)

# ---------------------------------------------------------------------------
# 数据源 1：500.com 历史走势页
# ---------------------------------------------------------------------------

_500_URL = "https://datachart.500.com/dlt/history/newinc/history.php?start={start}&end=99999"


def _fetch_from_500com(after_issue: Optional[str] = None) -> List[Dict[str, str]]:
    start = "07001"
    if after_issue:
        num = int(re.sub(r"^20", "", after_issue))
        start = str(num)
    resp = requests.get(
        _500_URL.format(start=start), headers=_REQUEST_HEADERS, timeout=30,
    )
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", id="tablelist") or soup.find("table", id="tdata")
    if not table:
        raise RuntimeError("500.com: DLT history table not found")
    results: List[Dict[str, str]] = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 15:
            continue
        raw_issue = tds[0].get_text(strip=True)
        if not raw_issue.isdigit():
            continue
        issue = ("20" + raw_issue) if len(raw_issue) == 5 else raw_issue
        if after_issue and issue <= after_issue:
            continue
        fronts = [tds[i].get_text(strip=True).zfill(2) for i in range(1, 6)]
        backs = [tds[6].get_text(strip=True).zfill(2), tds[7].get_text(strip=True).zfill(2)]
        date_str = tds[14].get_text(strip=True)
        results.append({
            "issue": issue, "date": date_str,
            "front1": fronts[0], "front2": fronts[1], "front3": fronts[2],
            "front4": fronts[3], "front5": fronts[4],
            "back1": backs[0], "back2": backs[1],
        })
    return results

# ---------------------------------------------------------------------------
# 数据源 2：500.com 主页面（备用 URL）
# ---------------------------------------------------------------------------

_500_MAIN_URL = "https://datachart.500.com/dlt/history/history.shtml"


def _fetch_from_500com_main(after_issue: Optional[str] = None) -> List[Dict[str, str]]:
    resp = requests.get(_500_MAIN_URL, headers=_REQUEST_HEADERS, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", id="tablelist") or soup.find("table", id="tdata")
    if not table:
        raise RuntimeError("500.com main: DLT history table not found")
    results: List[Dict[str, str]] = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 15:
            continue
        raw_issue = tds[0].get_text(strip=True)
        if not raw_issue.isdigit():
            continue
        issue = ("20" + raw_issue) if len(raw_issue) == 5 else raw_issue
        if after_issue and issue <= after_issue:
            continue
        fronts = [tds[i].get_text(strip=True).zfill(2) for i in range(1, 6)]
        backs = [tds[6].get_text(strip=True).zfill(2), tds[7].get_text(strip=True).zfill(2)]
        date_str = tds[14].get_text(strip=True)
        results.append({
            "issue": issue, "date": date_str,
            "front1": fronts[0], "front2": fronts[1], "front3": fronts[2],
            "front4": fronts[3], "front5": fronts[4],
            "back1": backs[0], "back2": backs[1],
        })
    return results

# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------

_SOURCES = [
    ("500.com", _fetch_from_500com),
    ("500.com主页", _fetch_from_500com_main),
]


def fetch_dlt_history() -> None:
    """拉取大乐透历史数据（增量更新）。"""
    bundled = _read_csv(BUNDLED_CSV)
    runtime = _read_csv(RUNTIME_CSV)
    local = _merge_records(bundled, runtime)
    latest_issue = _max_issue(local)

    logger.info("本地数据 %d 条，最新期号 %s", len(local), latest_issue)

    new_records: List[Dict[str, str]] = []
    last_error: Optional[Exception] = None

    for name, fetcher in _SOURCES:
        try:
            new_records = fetcher(after_issue=latest_issue)
            if new_records:
                logger.info("%s: 获取到 %d 条新数据", name, len(new_records))
            else:
                logger.info("%s: 无新数据", name)
            last_error = None
            break
        except Exception as exc:
            logger.warning("%s 拉取失败: %s", name, exc)
            last_error = exc
            continue

    if last_error and not local:
        raise RuntimeError(
            f"所有数据源均不可用且无本地数据: {last_error}"
        ) from last_error

    all_records = _merge_records(local, new_records)
    _write_csv(RUNTIME_CSV, all_records)
    logger.info("写入 %s，共 %d 条", RUNTIME_CSV, len(all_records))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    fetch_dlt_history()

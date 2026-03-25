"""双色球数据拉取：本地优先 + 增量更新 + 多源容错。

策略：
1. 加载 bundled 历史数据（随代码发布，不可变）
2. 加载 runtime CSV（之前增量写入的）
3. 合并去重得到已有数据集
4. 依次尝试在线数据源，仅拉取比本地更新的期号（增量）
5. 合并新数据并写回 runtime CSV
6. 所有在线源都失败时，若本地已有足够数据则静默降级而非报错
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

BUNDLED_CSV = Path(__file__).resolve().parent.parent / "data" / "ssq_history_bundled.csv"
RUNTIME_CSV = DATA_DIR / "ssq_history.csv"
FIELDNAMES = ["issue", "date", "red1", "red2", "red3", "red4", "red5", "red6", "blue1"]

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
    """合并多份记录，以 issue 去重（后出现的覆盖）并按 issue 升序排列。"""
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
# 数据源 1：CWL 官方 API（中国福利彩票官网）
# ---------------------------------------------------------------------------

_CWL_API = (
    "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
    "?name=ssq&issueCount=&issueStart=&issueEnd="
    "&dayStart=&dayEnd=&pageNo={page}&pageSize=100&week=&systemType=PC"
)


def _fetch_from_cwl(after_issue: Optional[str] = None) -> List[Dict[str, str]]:
    """从福彩官网 API 拉取数据，仅返回 issue > after_issue 的记录。"""
    headers = {**_REQUEST_HEADERS, "Referer": "https://www.cwl.gov.cn/ygkj/wqkjgg/ssq/"}
    results: List[Dict[str, str]] = []
    for page in range(1, 15):
        resp = requests.get(_CWL_API.format(page=page), headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            data = data.get("result", data)
            if isinstance(data, dict):
                data = data.get("data", [])
        if not data:
            break
        for item in data:
            code = str(item["code"])
            if after_issue and code <= after_issue:
                return results
            date_raw = item["date"].split("(")[0]
            reds = item["red"].split(",")
            results.append({
                "issue": code,
                "date": date_raw,
                "red1": reds[0], "red2": reds[1], "red3": reds[2],
                "red4": reds[3], "red5": reds[4], "red6": reds[5],
                "blue1": item["blue"],
            })
        if len(data) < 100:
            break
    return results

# ---------------------------------------------------------------------------
# 数据源 2：500.com 历史走势页（HTML 解析）
# ---------------------------------------------------------------------------

_500_URL = "https://datachart.500.com/ssq/history/newinc/history.php?start={start}&end=99999"


def _fetch_from_500com(after_issue: Optional[str] = None) -> List[Dict[str, str]]:
    """从 500.com 抓取历史数据，仅返回 issue > after_issue 的记录。"""
    start = "03001"
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
        raise RuntimeError("500.com: history table not found")
    results: List[Dict[str, str]] = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 16:
            continue
        raw_issue = tds[0].get_text(strip=True)
        if not raw_issue.isdigit():
            continue
        issue = ("20" + raw_issue) if len(raw_issue) == 5 else raw_issue
        if after_issue and issue <= after_issue:
            continue
        reds = [tds[i].get_text(strip=True).zfill(2) for i in range(1, 7)]
        blue = tds[7].get_text(strip=True).zfill(2)
        date_str = tds[15].get_text(strip=True)
        results.append({
            "issue": issue, "date": date_str,
            "red1": reds[0], "red2": reds[1], "red3": reds[2],
            "red4": reds[3], "red5": reds[4], "red6": reds[5],
            "blue1": blue,
        })
    return results

# ---------------------------------------------------------------------------
# 公开接口
# ---------------------------------------------------------------------------

_SOURCES = [
    ("CWL官方API", _fetch_from_cwl),
    ("500.com", _fetch_from_500com),
]


def fetch_ssq_history() -> None:
    """拉取双色球历史数据（增量更新）。

    加载 bundled + runtime 本地数据后，逐个尝试在线数据源做增量补充。
    所有在线源均失败时，若本地数据非空则静默降级。
    """
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
    fetch_ssq_history()

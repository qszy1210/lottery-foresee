from __future__ import annotations

import csv
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from app.config import DATA_DIR


BASE_URL = "https://datachart.500.com/ssq/history/history.shtml"


def fetch_ssq_history() -> None:
    resp = requests.get(BASE_URL, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table", id="tdata")
    if not table:
        raise RuntimeError("History table not found")
    rows = table.find_all("tr")
    records = []
    for tr in rows:
        tds = tr.find_all("td")
        if len(tds) < 16:
            continue
        issue = tds[0].get_text(strip=True)
        date = tds[15].get_text(strip=True)
        reds = [tds[i].get_text(strip=True) for i in range(1, 7)]
        blue = tds[7].get_text(strip=True)
        records.append(
            {
                "issue": issue,
                "date": date,
                "red1": reds[0],
                "red2": reds[1],
                "red3": reds[2],
                "red4": reds[3],
                "red5": reds[4],
                "red6": reds[5],
                "blue1": blue,
            }
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DATA_DIR / "ssq_history.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "issue",
                "date",
                "red1",
                "red2",
                "red3",
                "red4",
                "red5",
                "red6",
                "blue1",
            ],
        )
        writer.writeheader()
        writer.writerows(records)


if __name__ == "__main__":
    fetch_ssq_history()


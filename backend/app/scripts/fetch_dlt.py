from __future__ import annotations

import csv
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from app.config import DATA_DIR


BASE_URL = "https://datachart.500.com/dlt/history/history.shtml"


def fetch_dlt_history() -> None:
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
        if len(tds) < 17:
            continue
        issue = tds[0].get_text(strip=True)
        date = tds[15].get_text(strip=True)
        fronts = [tds[i].get_text(strip=True) for i in range(1, 6)]
        backs = [tds[6].get_text(strip=True), tds[7].get_text(strip=True)]
        records.append(
            {
                "issue": issue,
                "date": date,
                "front1": fronts[0],
                "front2": fronts[1],
                "front3": fronts[2],
                "front4": fronts[3],
                "front5": fronts[4],
                "back1": backs[0],
                "back2": backs[1],
            }
        )

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DATA_DIR / "dlt_history.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "issue",
                "date",
                "front1",
                "front2",
                "front3",
                "front4",
                "front5",
                "back1",
                "back2",
            ],
        )
        writer.writeheader()
        writer.writerows(records)


if __name__ == "__main__":
    fetch_dlt_history()


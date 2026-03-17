"""生成示例 CSV，便于无网络时后端仍可启动并响应预测。"""
from __future__ import annotations

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def gen_ssq_csv(path: Path, rows: int = 120) -> None:
    random.seed(42)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["issue", "date", "red1", "red2", "red3", "red4", "red5", "red6", "blue1"])
        for i in range(rows):
            issue = f"2024001{i:03d}"[-7:] if i < 1000 else f"2025{i:03d}"
            date_str = f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"
            reds = sorted(random.sample(range(1, 34), 6))
            blue = random.randint(1, 16)
            w.writerow([issue, date_str] + reds + [blue])


def gen_dlt_csv(path: Path, rows: int = 120) -> None:
    random.seed(43)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["issue", "date", "front1", "front2", "front3", "front4", "front5", "back1", "back2"])
        for i in range(rows):
            issue = f"24001{i:03d}"[-7:] if i < 1000 else f"250{i:03d}"
            date_str = f"2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}"
            fronts = sorted(random.sample(range(1, 36), 5))
            backs = sorted(random.sample(range(1, 13), 2))
            w.writerow([issue, date_str] + fronts + backs)


if __name__ == "__main__":
    ssq_path = DATA_DIR / "ssq_history.csv"
    dlt_path = DATA_DIR / "dlt_history.csv"
    gen_ssq_csv(ssq_path)
    gen_dlt_csv(dlt_path)
    print("Generated:", ssq_path, dlt_path)

from __future__ import annotations

from app.services.backtest_service import backtest_ssq, backtest_dlt


def main() -> None:
    ssq_result = backtest_ssq(window_size=100, sample_size=5000, issues=50)
    print("SSQ backtest on", ssq_result.total_issues, "issues")
    avg_reds = sum(d.hit_reds or 0 for d in ssq_result.details) / ssq_result.total_issues
    avg_blue = sum(d.hit_blue or 0 for d in ssq_result.details) / ssq_result.total_issues
    print("Avg red hits:", avg_reds, "Avg blue hits:", avg_blue)

    dlt_result = backtest_dlt(window_size=100, sample_size=5000, issues=50)
    print("DLT backtest on", dlt_result.total_issues, "issues")
    avg_fronts = sum(d.hit_fronts or 0 for d in dlt_result.details) / dlt_result.total_issues
    avg_backs = sum(d.hit_backs or 0 for d in dlt_result.details) / dlt_result.total_issues
    print("Avg front hits:", avg_fronts, "Avg back hits:", avg_backs)


if __name__ == "__main__":
    main()


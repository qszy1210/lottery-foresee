from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Sequence

from app.config import settings
from app.domain.models import SsqDraw, DltDraw, SsqCombination, DltCombination
from app.domain.simulation import generate_ssq_candidates, generate_dlt_candidates
from app.domain.scoring import score_ssq_combination, score_dlt_combination, rank_combinations
from app.domain.stats import ssq_frequency, dlt_frequency
from app.services.data_service import load_ssq_history, load_dlt_history


@dataclass
class HitDetail:
    issue: str
    hit_reds: int | None = None
    hit_blue: int | None = None
    hit_fronts: int | None = None
    hit_backs: int | None = None


@dataclass
class BacktestResult:
    details: List[HitDetail]
    total_issues: int


def _best_ssq_for_issue(history: List[SsqDraw], sample_size: int) -> SsqCombination:
    red_freq, blue_freq = ssq_frequency(history)
    candidates = generate_ssq_candidates(
        red_probs=red_freq.probabilities,
        blue_probs=blue_freq.probabilities,
        sample_size=sample_size,
        red_range=range(1, 34),
        blue_range=range(1, 17),
    )
    ranked = rank_combinations(
        candidates,
        lambda c: score_ssq_combination(c, red_freq, blue_freq),
    )
    return ranked[0].combination  # type: ignore[return-value]


def _best_dlt_for_issue(history: List[DltDraw], sample_size: int) -> DltCombination:
    front_freq, back_freq = dlt_frequency(history)
    candidates = generate_dlt_candidates(
        front_probs=front_freq.probabilities,
        back_probs=back_freq.probabilities,
        sample_size=sample_size,
        front_range=range(1, 36),
        back_range=range(1, 13),
    )
    ranked = rank_combinations(
        candidates,
        lambda c: score_dlt_combination(c, front_freq, back_freq),
    )
    return ranked[0].combination  # type: ignore[return-value]


def backtest_ssq(window_size: int, sample_size: int, issues: int) -> BacktestResult:
    draws = load_ssq_history()
    details: List[HitDetail] = []
    # 从较早的期次开始，预留 window_size 作为历史窗口
    start_index = window_size
    end_index = min(len(draws), start_index + issues)
    for idx in range(start_index, end_index):
        history_window = draws[idx - window_size : idx]
        target = draws[idx]
        best_combo = _best_ssq_for_issue(history_window, sample_size)
        hit_reds = len(set(best_combo.reds) & set(target.reds))
        hit_blue = 1 if best_combo.blue == target.blue else 0
        details.append(
            HitDetail(
                issue=target.issue,
                hit_reds=hit_reds,
                hit_blue=hit_blue,
            )
        )
    return BacktestResult(details=details, total_issues=len(details))


def backtest_dlt(window_size: int, sample_size: int, issues: int) -> BacktestResult:
    draws = load_dlt_history()
    details: List[HitDetail] = []
    start_index = window_size
    end_index = min(len(draws), start_index + issues)
    for idx in range(start_index, end_index):
        history_window = draws[idx - window_size : idx]
        target = draws[idx]
        best_combo = _best_dlt_for_issue(history_window, sample_size)
        hit_fronts = len(set(best_combo.fronts) & set(target.fronts))
        hit_backs = len(set(best_combo.backs) & set(target.backs))
        details.append(
            HitDetail(
                issue=target.issue,
                hit_fronts=hit_fronts,
                hit_backs=hit_backs,
            )
        )
    return BacktestResult(details=details, total_issues=len(details))


from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from app.domain.stats import (
    ssq_frequency,
    ssq_omission,
    ssq_sum_stats,
    dlt_frequency,
    dlt_omission,
    dlt_sum_stats,
)
from app.services.data_service import load_ssq_history, load_dlt_history


@dataclass
class NumberStat:
    number: int
    count: int
    probability: float
    omission: int


@dataclass
class SsqStatsSummary:
    total_draws: int
    reds: List[NumberStat]
    blues: List[NumberStat]


@dataclass
class DltStatsSummary:
    total_draws: int
    fronts: List[NumberStat]
    backs: List[NumberStat]


def get_ssq_stats_summary() -> SsqStatsSummary:
    draws = load_ssq_history()
    red_freq, blue_freq = ssq_frequency(draws)
    red_omission, blue_omission = ssq_omission(draws, range(1, 34), range(1, 17))
    reds: List[NumberStat] = []
    for n in range(1, 34):
        count = red_freq.counts.get(n, 0)
        prob = red_freq.probabilities.get(n, 0.0)
        omit = red_omission.omissions.get(n, 0)
        reds.append(NumberStat(number=n, count=count, probability=prob, omission=omit))
    blues: List[NumberStat] = []
    for n in range(1, 17):
        count = blue_freq.counts.get(n, 0)
        prob = blue_freq.probabilities.get(n, 0.0)
        omit = blue_omission.omissions.get(n, 0)
        blues.append(NumberStat(number=n, count=count, probability=prob, omission=omit))
    return SsqStatsSummary(total_draws=len(draws), reds=reds, blues=blues)


def get_dlt_stats_summary() -> DltStatsSummary:
    draws = load_dlt_history()
    front_freq, back_freq = dlt_frequency(draws)
    front_omission, back_omission = dlt_omission(draws, range(1, 36), range(1, 13))
    fronts: List[NumberStat] = []
    for n in range(1, 36):
        count = front_freq.counts.get(n, 0)
        prob = front_freq.probabilities.get(n, 0.0)
        omit = front_omission.omissions.get(n, 0)
        fronts.append(NumberStat(number=n, count=count, probability=prob, omission=omit))
    backs: List[NumberStat] = []
    for n in range(1, 13):
        count = back_freq.counts.get(n, 0)
        prob = back_freq.probabilities.get(n, 0.0)
        omit = back_omission.omissions.get(n, 0)
        backs.append(NumberStat(number=n, count=count, probability=prob, omission=omit))
    return DltStatsSummary(total_draws=len(draws), fronts=fronts, backs=backs)


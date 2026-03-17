from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from .models import SsqDraw, DltDraw


@dataclass
class FrequencyStats:
    counts: Dict[int, int]
    total: int

    @property
    def probabilities(self) -> Dict[int, float]:
        if self.total == 0:
            return {}
        return {k: v / self.total for k, v in self.counts.items()}


@dataclass
class OmissionStats:
    omissions: Dict[int, int]


@dataclass
class SumStats:
    sums: List[int]


def _flatten(values: Iterable[Iterable[int]]) -> List[int]:
    return [x for seq in values for x in seq]


def ssq_frequency(draws: List[SsqDraw]) -> Tuple[FrequencyStats, FrequencyStats]:
    red_values = _flatten(d.reds for d in draws)
    blue_values = [d.blue for d in draws]
    red_counts = Counter(red_values)
    blue_counts = Counter(blue_values)
    return FrequencyStats(dict(red_counts), len(red_values)), FrequencyStats(
        dict(blue_counts), len(blue_values)
    )


def ssq_omission(draws: List[SsqDraw], red_range: range, blue_range: range) -> Tuple[OmissionStats, OmissionStats]:
    red_last_seen: Dict[int, int] = {n: -1 for n in red_range}
    blue_last_seen: Dict[int, int] = {n: -1 for n in blue_range}
    for idx, d in enumerate(draws):
        for r in d.reds:
            red_last_seen[r] = idx
        blue_last_seen[d.blue] = idx
    last_index = len(draws) - 1
    red_omissions = {n: (last_index - red_last_seen[n]) if red_last_seen[n] != -1 else last_index + 1 for n in red_range}
    blue_omissions = {n: (last_index - blue_last_seen[n]) if blue_last_seen[n] != -1 else last_index + 1 for n in blue_range}
    return OmissionStats(red_omissions), OmissionStats(blue_omissions)


def ssq_sum_stats(draws: List[SsqDraw]) -> SumStats:
    sums = [sum(d.reds) + d.blue for d in draws]
    return SumStats(sums)


def dlt_frequency(draws: List[DltDraw]) -> Tuple[FrequencyStats, FrequencyStats]:
    front_values = _flatten(d.fronts for d in draws)
    back_values = _flatten(d.backs for d in draws)
    front_counts = Counter(front_values)
    back_counts = Counter(back_values)
    return FrequencyStats(dict(front_counts), len(front_values)), FrequencyStats(
        dict(back_counts), len(back_values)
    )


def dlt_omission(draws: List[DltDraw], front_range: range, back_range: range) -> Tuple[OmissionStats, OmissionStats]:
    front_last_seen: Dict[int, int] = {n: -1 for n in front_range}
    back_last_seen: Dict[int, int] = {n: -1 for n in back_range}
    for idx, d in enumerate(draws):
        for f in d.fronts:
            front_last_seen[f] = idx
        for b in d.backs:
            back_last_seen[b] = idx
    last_index = len(draws) - 1
    front_omissions = {n: (last_index - front_last_seen[n]) if front_last_seen[n] != -1 else last_index + 1 for n in front_range}
    back_omissions = {n: (last_index - back_last_seen[n]) if back_last_seen[n] != -1 else last_index + 1 for n in back_range}
    return OmissionStats(front_omissions), OmissionStats(back_omissions)


def dlt_sum_stats(draws: List[DltDraw]) -> SumStats:
    sums = [sum(d.fronts) + sum(d.backs) for d in draws]
    return SumStats(sums)


from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .models import SsqCombination, DltCombination
from .stats import FrequencyStats


@dataclass
class ScoredCombination:
    score: float
    combination: object


def score_ssq_combination(
    combo: SsqCombination,
    red_freq: FrequencyStats,
    blue_freq: FrequencyStats,
) :  # returns float
    red_score = sum(red_freq.probabilities.get(r, 0.0) for r in combo.reds)
    blue_score = blue_freq.probabilities.get(combo.blue, 0.0)
    return red_score + blue_score


def score_dlt_combination(
    combo: DltCombination,
    front_freq: FrequencyStats,
    back_freq: FrequencyStats,
) :  # returns float
    front_score = sum(front_freq.probabilities.get(f, 0.0) for f in combo.fronts)
    back_score = sum(back_freq.probabilities.get(b, 0.0) for b in combo.backs)
    return front_score + back_score


def rank_combinations(combos: List[object], scorer) -> List[ScoredCombination]:
    scored = [ScoredCombination(score=scorer(c), combination=c) for c in combos]
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored


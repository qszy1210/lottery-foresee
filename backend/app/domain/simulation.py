from __future__ import annotations

import random
from typing import Dict, List, Tuple

from .models import SsqCombination, DltCombination


def _weighted_sample_without_replacement(numbers: List[int], weights: Dict[int, float], k: int) -> List[int]:
    pool = numbers[:]
    chosen: List[int] = []
    for _ in range(k):
        total_w = sum(weights.get(n, 1.0) for n in pool)
        if total_w == 0:
            idx = random.randrange(len(pool))
            n = pool.pop(idx)
            chosen.append(n)
            continue
        r = random.random() * total_w
        acc = 0.0
        for i, n in enumerate(pool):
            acc += weights.get(n, 1.0)
            if acc >= r:
                chosen.append(n)
                pool.pop(i)
                break
    chosen.sort()
    return chosen


def generate_ssq_candidates(
    red_probs: Dict[int, float],
    blue_probs: Dict[int, float],
    sample_size: int,
    red_range: range,
    blue_range: range,
) -> List[SsqCombination]:
    red_numbers = list(red_range)
    blue_numbers = list(blue_range)
    combos: List[SsqCombination] = []
    for _ in range(sample_size):
        reds = _weighted_sample_without_replacement(red_numbers, red_probs, 6)
        blue = random.choices(blue_numbers, weights=[blue_probs.get(b, 1.0) for b in blue_numbers], k=1)[0]
        combos.append(SsqCombination(reds=reds, blue=blue))
    return combos


def generate_dlt_candidates(
    front_probs: Dict[int, float],
    back_probs: Dict[int, float],
    sample_size: int,
    front_range: range,
    back_range: range,
) -> List[DltCombination]:
    front_numbers = list(front_range)
    back_numbers = list(back_range)
    combos: List[DltCombination] = []
    for _ in range(sample_size):
        fronts = _weighted_sample_without_replacement(front_numbers, front_probs, 5)
        backs = _weighted_sample_without_replacement(back_numbers, back_probs, 2)
        combos.append(DltCombination(fronts=fronts, backs=backs))
    return combos


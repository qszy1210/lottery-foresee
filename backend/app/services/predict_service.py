from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

from app.config import settings
from app.domain.models import SsqCombination, DltCombination
from app.domain.scoring import (
    ScoredCombination,
    rank_combinations,
    score_ssq_combination,
    score_dlt_combination,
)
from app.domain.simulation import generate_ssq_candidates, generate_dlt_candidates
from app.domain.stats import ssq_frequency, dlt_frequency
from app.services.data_service import load_ssq_history, load_dlt_history
from app.services.compare_service import get_ssq_correction_weights, get_dlt_correction_weights


@dataclass
class SsqRecommendation:
    reds: List[int]
    blue: int
    score: float


@dataclass
class DltRecommendation:
    fronts: List[int]
    backs: List[int]
    score: float


def _apply_correction(probs: dict, correction: dict, default: float = 1.0) -> dict:
    if not correction:
        return probs
    return {k: probs.get(k, 0.0) * correction.get(k, default) for k in set(probs) | set(correction) or probs}


def recommend_ssq(
    window_size: int | None = None,
    sample_size: int | None = None,
    recommend_count: int | None = None,
    seed: int | None = None,
    use_correction: bool = False,
) -> List[SsqRecommendation]:
    params = settings.model_params
    window_size = window_size or params.window_size
    sample_size = sample_size or params.sample_size
    recommend_count = recommend_count or params.recommend_count
    if seed is not None:
        random.seed(seed)
    draws = load_ssq_history()
    history = draws[-window_size:] if window_size < len(draws) else draws
    red_freq, blue_freq = ssq_frequency(history)
    red_probs = red_freq.probabilities
    blue_probs = blue_freq.probabilities
    if use_correction:
        red_corr, blue_corr = get_ssq_correction_weights()
        if red_corr:
            red_probs = _apply_correction(red_freq.probabilities, red_corr)
        if blue_corr:
            blue_probs = _apply_correction(blue_freq.probabilities, blue_corr)
    candidates = generate_ssq_candidates(
        red_probs=red_probs,
        blue_probs=blue_probs,
        sample_size=sample_size,
        red_range=range(1, 34),
        blue_range=range(1, 17),
    )
    ranked = rank_combinations(
        candidates,
        lambda c: score_ssq_combination(c, red_freq, blue_freq),
    )
    top = ranked[:recommend_count]
    return [
        SsqRecommendation(
            reds=list(c.combination.reds),  # type: ignore[attr-defined]
            blue=c.combination.blue,  # type: ignore[attr-defined]
            score=c.score,
        )
        for c in top
    ]


def recommend_dlt(
    window_size: int | None = None,
    sample_size: int | None = None,
    recommend_count: int | None = None,
    seed: int | None = None,
    use_correction: bool = False,
) -> List[DltRecommendation]:
    params = settings.model_params
    window_size = window_size or params.window_size
    sample_size = sample_size or params.sample_size
    recommend_count = recommend_count or params.recommend_count
    if seed is not None:
        random.seed(seed)
    draws = load_dlt_history()
    history = draws[-window_size:] if window_size < len(draws) else draws
    front_freq, back_freq = dlt_frequency(history)
    front_probs = front_freq.probabilities
    back_probs = back_freq.probabilities
    if use_correction:
        front_corr, back_corr = get_dlt_correction_weights()
        if front_corr:
            front_probs = _apply_correction(front_freq.probabilities, front_corr)
        if back_corr:
            back_probs = _apply_correction(back_freq.probabilities, back_corr)
    candidates = generate_dlt_candidates(
        front_probs=front_probs,
        back_probs=back_probs,
        sample_size=sample_size,
        front_range=range(1, 36),
        back_range=range(1, 13),
    )
    ranked = rank_combinations(
        candidates,
        lambda c: score_dlt_combination(c, front_freq, back_freq),
    )
    top = ranked[:recommend_count]
    return [
        DltRecommendation(
            fronts=list(c.combination.fronts),  # type: ignore[attr-defined]
            backs=list(c.combination.backs),  # type: ignore[attr-defined]
            score=c.score,
        )
        for c in top
    ]


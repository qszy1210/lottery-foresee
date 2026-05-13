from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Literal

from app.config import settings
from app.domain.models import SsqCombination, DltCombination
from app.domain.scoring import (
    ScoredCombination,
    rank_combinations,
    score_ssq_combination,
    score_dlt_combination,
)
from app.domain.simulation import (
    generate_ssq_candidates,
    generate_dlt_candidates,
    generate_ssq_shock_combination,
    generate_dlt_shock_combination,
    generate_ssq_random_shock_combination,
    generate_dlt_random_shock_combination,
)
from app.domain.stats import ssq_frequency, dlt_frequency
from app.services.data_service import load_ssq_history, load_dlt_history
from app.services.compare_service import get_ssq_correction_weights, get_dlt_correction_weights


RecommendationKind = Literal["main", "shock", "random_shock"]


@dataclass
class SsqRecommendation:
    reds: List[int]
    blue: int
    score: float
    # kind 默认为 main，保持与既有调用方/前端兼容；shock 用于震荡推荐
    kind: RecommendationKind = "main"


@dataclass
class DltRecommendation:
    fronts: List[int]
    backs: List[int]
    score: float
    kind: RecommendationKind = "main"


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
    include_shock: bool = True,
    include_random_shock: bool = True,
    random_shock_perturb: int = 2,
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
    main_recs: List[SsqRecommendation] = [
        SsqRecommendation(
            reds=list(c.combination.reds),  # type: ignore[attr-defined]
            blue=c.combination.blue,  # type: ignore[attr-defined]
            score=c.score,
            kind="main",
        )
        for c in top
    ]
    if not main_recs:
        return main_recs

    main_combos = [SsqCombination(reds=r.reds, blue=r.blue) for r in main_recs]

    # 震荡推荐：基于主推荐结果做一次扰动重组，独立 RNG 保证不影响主推荐
    if include_shock:
        shock_rng = random.Random(seed if seed is not None else random.randrange(2**31))
        shock_combo = generate_ssq_shock_combination(
            main_combinations=main_combos,
            red_probs=red_probs,
            blue_probs=blue_probs,
            red_range=range(1, 34),
            blue_range=range(1, 17),
            rng=shock_rng,
        )
        shock_score = score_ssq_combination(shock_combo, red_freq, blue_freq)
        main_recs.append(
            SsqRecommendation(
                reds=list(shock_combo.reds),
                blue=shock_combo.blue,
                score=shock_score,
                kind="shock",
            )
        )

    # 无规律震荡：基于主推荐 #1 纯随机替换 perturb 个号码，独立 RNG
    if include_random_shock:
        rs_seed = (seed + 1) if seed is not None else random.randrange(2**31)
        rs_rng = random.Random(rs_seed)
        base = main_combos[0]
        rs_combo = generate_ssq_random_shock_combination(
            base_combination=base,
            red_range=range(1, 34),
            blue_range=range(1, 17),
            perturb_count=random_shock_perturb,
            rng=rs_rng,
        )
        rs_score = score_ssq_combination(rs_combo, red_freq, blue_freq)
        main_recs.append(
            SsqRecommendation(
                reds=list(rs_combo.reds),
                blue=rs_combo.blue,
                score=rs_score,
                kind="random_shock",
            )
        )
    return main_recs


def recommend_dlt(
    window_size: int | None = None,
    sample_size: int | None = None,
    recommend_count: int | None = None,
    seed: int | None = None,
    use_correction: bool = False,
    include_shock: bool = True,
    include_random_shock: bool = True,
    random_shock_perturb: int = 2,
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
    main_recs: List[DltRecommendation] = [
        DltRecommendation(
            fronts=list(c.combination.fronts),  # type: ignore[attr-defined]
            backs=list(c.combination.backs),  # type: ignore[attr-defined]
            score=c.score,
            kind="main",
        )
        for c in top
    ]
    if not main_recs:
        return main_recs

    main_combos = [DltCombination(fronts=r.fronts, backs=r.backs) for r in main_recs]

    if include_shock:
        shock_rng = random.Random(seed if seed is not None else random.randrange(2**31))
        shock_combo = generate_dlt_shock_combination(
            main_combinations=main_combos,
            front_probs=front_probs,
            back_probs=back_probs,
            front_range=range(1, 36),
            back_range=range(1, 13),
            rng=shock_rng,
        )
        shock_score = score_dlt_combination(shock_combo, front_freq, back_freq)
        main_recs.append(
            DltRecommendation(
                fronts=list(shock_combo.fronts),
                backs=list(shock_combo.backs),
                score=shock_score,
                kind="shock",
            )
        )

    if include_random_shock:
        rs_seed = (seed + 1) if seed is not None else random.randrange(2**31)
        rs_rng = random.Random(rs_seed)
        base = main_combos[0]
        rs_combo = generate_dlt_random_shock_combination(
            base_combination=base,
            front_range=range(1, 36),
            back_range=range(1, 13),
            perturb_count=random_shock_perturb,
            rng=rs_rng,
        )
        rs_score = score_dlt_combination(rs_combo, front_freq, back_freq)
        main_recs.append(
            DltRecommendation(
                fronts=list(rs_combo.fronts),
                backs=list(rs_combo.backs),
                score=rs_score,
                kind="random_shock",
            )
        )
    return main_recs


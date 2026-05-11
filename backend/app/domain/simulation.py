from __future__ import annotations

import random
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .models import SsqCombination, DltCombination


def _weighted_sample_without_replacement(
    numbers: List[int],
    weights: Dict[int, float],
    k: int,
    rng: Optional[random.Random] = None,
) -> List[int]:
    """从 numbers 中按 weights 不放回抽样 k 个；rng 为 None 时使用全局 random。"""
    rand = rng if rng is not None else random
    pool = numbers[:]
    chosen: List[int] = []
    for _ in range(k):
        total_w = sum(weights.get(n, 1.0) for n in pool)
        if total_w == 0:
            idx = rand.randrange(len(pool))
            n = pool.pop(idx)
            chosen.append(n)
            continue
        r = rand.random() * total_w
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


# ---------------------------------------------------------------------------
# 震荡推荐（基于主推荐结果的"扰动重组"）
# ---------------------------------------------------------------------------
#
# 设计目标：在 N 组主推荐之外，额外给出 1 注"震荡号码"。
# 它不是按概率收敛的最优组合，也不是纯随机，而是：
#   1) 保留主推荐里出现频次较高的号码作为"基底"（继承）；
#   2) 剩余位置从"未被主推荐选中的号码"中抽取，权重用
#      α * 反向概率（让冷门号有机会） + (1-α) * 均匀随机
#      组合而成，制造可控的"震荡感"。
# 这样既保留了原推荐的痕迹（用户能看到熟悉的号码），
# 又有突破收敛偏好的扰动空间。


def _count_numbers(items: Iterable[Sequence[int]]) -> Dict[int, int]:
    """统计号码在多组结果里出现的次数。"""
    counts: Dict[int, int] = {}
    for group in items:
        for n in group:
            counts[n] = counts.get(n, 0) + 1
    return counts


def _shock_weights(
    candidates: List[int],
    probs: Dict[int, float],
    *,
    alpha: float = 0.6,
    epsilon: float = 1e-3,
) -> Dict[int, float]:
    """为震荡补全位生成权重：α * 反向概率 + (1-α) * 均匀。

    - 反向概率：max(0, mean_prob - probs[n])，原本越冷门权重越大；
    - 均匀分量：保证全集都有非零概率；
    - epsilon：再加一个小常数避免极端情况下全 0。
    """
    if not candidates:
        return {}
    probs_for_pool = [probs.get(n, 0.0) for n in candidates]
    mean_prob = sum(probs_for_pool) / len(candidates) if candidates else 0.0
    max_inv = 0.0
    inverse: Dict[int, float] = {}
    for n in candidates:
        inv = max(0.0, mean_prob - probs.get(n, 0.0))
        inverse[n] = inv
        if inv > max_inv:
            max_inv = inv
    weights: Dict[int, float] = {}
    for n in candidates:
        inv_norm = inverse[n] / max_inv if max_inv > 0 else 0.0
        weights[n] = alpha * inv_norm + (1.0 - alpha) + epsilon
    return weights


def _pick_from_base(
    base_counts: Dict[int, int],
    k: int,
    rng: random.Random,
) -> List[int]:
    """从主推荐号码池里按频次加权不放回抽 k 个；k 大于池子大小则全部取出。"""
    if k <= 0 or not base_counts:
        return []
    pool = list(base_counts.keys())
    weights = {n: float(base_counts[n]) for n in pool}
    k_eff = min(k, len(pool))
    return _weighted_sample_without_replacement(pool, weights, k_eff, rng=rng)


def generate_ssq_shock_combination(
    main_combinations: Sequence[SsqCombination],
    red_probs: Dict[int, float],
    blue_probs: Dict[int, float],
    red_range: range,
    blue_range: range,
    *,
    keep_reds: int = 3,
    rng: Optional[random.Random] = None,
) -> SsqCombination:
    """基于主推荐生成一注双色球震荡号码。

    参数：
    - main_combinations：主推荐的若干组（按打分排序后的列表）。
    - keep_reds：从主推荐红球池里继承的个数（红球共 6 个）。
    """
    rand = rng if rng is not None else random.Random()
    red_base_counts = _count_numbers([c.reds for c in main_combinations])
    blue_base_counts = _count_numbers([[c.blue] for c in main_combinations])

    kept_reds = _pick_from_base(red_base_counts, keep_reds, rand)
    remaining_reds = [n for n in red_range if n not in kept_reds]
    needed = 6 - len(kept_reds)
    if needed > 0:
        weights = _shock_weights(remaining_reds, red_probs)
        filler = _weighted_sample_without_replacement(remaining_reds, weights, needed, rng=rand)
    else:
        filler = []
    reds = sorted(set(kept_reds) | set(filler))

    blue_pool = list(blue_range)
    used_blues = [b for b in blue_base_counts.keys() if b in blue_pool]
    unused_blues = [b for b in blue_pool if b not in used_blues]
    if used_blues and unused_blues:
        if rand.random() < 0.5:
            blue = rand.choice(used_blues)
        else:
            weights = _shock_weights(unused_blues, blue_probs)
            blue = _weighted_sample_without_replacement(unused_blues, weights, 1, rng=rand)[0]
    elif unused_blues:
        weights = _shock_weights(unused_blues, blue_probs)
        blue = _weighted_sample_without_replacement(unused_blues, weights, 1, rng=rand)[0]
    elif used_blues:
        blue = rand.choice(used_blues)
    else:
        blue = rand.choice(blue_pool)

    return SsqCombination(reds=reds, blue=blue)


def generate_dlt_shock_combination(
    main_combinations: Sequence[DltCombination],
    front_probs: Dict[int, float],
    back_probs: Dict[int, float],
    front_range: range,
    back_range: range,
    *,
    keep_fronts: int = 2,
    keep_backs: int = 1,
    rng: Optional[random.Random] = None,
) -> DltCombination:
    """基于主推荐生成一注大乐透震荡号码。"""
    rand = rng if rng is not None else random.Random()
    front_base_counts = _count_numbers([c.fronts for c in main_combinations])
    back_base_counts = _count_numbers([c.backs for c in main_combinations])

    kept_fronts = _pick_from_base(front_base_counts, keep_fronts, rand)
    remaining_fronts = [n for n in front_range if n not in kept_fronts]
    needed_f = 5 - len(kept_fronts)
    if needed_f > 0:
        weights = _shock_weights(remaining_fronts, front_probs)
        filler_f = _weighted_sample_without_replacement(remaining_fronts, weights, needed_f, rng=rand)
    else:
        filler_f = []
    fronts = sorted(set(kept_fronts) | set(filler_f))

    kept_backs = _pick_from_base(back_base_counts, keep_backs, rand)
    remaining_backs = [n for n in back_range if n not in kept_backs]
    needed_b = 2 - len(kept_backs)
    if needed_b > 0:
        weights = _shock_weights(remaining_backs, back_probs)
        filler_b = _weighted_sample_without_replacement(remaining_backs, weights, needed_b, rng=rand)
    else:
        filler_b = []
    backs = sorted(set(kept_backs) | set(filler_b))

    return DltCombination(fronts=fronts, backs=backs)


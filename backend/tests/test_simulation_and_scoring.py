import random

from app.domain.models import SsqCombination, DltCombination
from app.domain.scoring import score_ssq_combination, score_dlt_combination
from app.domain.stats import FrequencyStats
from app.domain.simulation import (
    generate_ssq_candidates,
    generate_dlt_candidates,
    generate_ssq_shock_combination,
    generate_dlt_shock_combination,
    generate_ssq_random_shock_combination,
    generate_dlt_random_shock_combination,
)


def test_generate_ssq_candidates_range_and_size():
    red_probs = {i: 1.0 for i in range(1, 34)}
    blue_probs = {i: 1.0 for i in range(1, 17)}
    combos = generate_ssq_candidates(red_probs, blue_probs, sample_size=20, red_range=range(1, 34), blue_range=range(1, 17))
    assert len(combos) == 20
    for c in combos:
        assert len(c.reds) == 6
        assert all(1 <= r <= 33 for r in c.reds)
        assert 1 <= c.blue <= 16


def test_generate_dlt_candidates_range_and_size():
    front_probs = {i: 1.0 for i in range(1, 36)}
    back_probs = {i: 1.0 for i in range(1, 13)}
    combos = generate_dlt_candidates(front_probs, back_probs, sample_size=20, front_range=range(1, 36), back_range=range(1, 13))
    assert len(combos) == 20
    for c in combos:
        assert len(c.fronts) == 5
        assert len(c.backs) == 2
        assert all(1 <= f <= 35 for f in c.fronts)
        assert all(1 <= b <= 12 for b in c.backs)


def test_scoring_monotonicity():
    red_freq = FrequencyStats(counts={1: 10, 2: 5}, total=15)
    blue_freq = FrequencyStats(counts={1: 5, 2: 10}, total=15)
    c1 = SsqCombination(reds=[1, 2, 3, 4, 5, 6], blue=1)
    c2 = SsqCombination(reds=[2, 3, 4, 5, 6, 7], blue=1)
    assert score_ssq_combination(c1, red_freq, blue_freq) > score_ssq_combination(c2, red_freq, blue_freq)

    front_freq = FrequencyStats(counts={1: 10, 2: 5}, total=15)
    back_freq = FrequencyStats(counts={1: 5, 2: 10}, total=15)
    d1 = DltCombination(fronts=[1, 2, 3, 4, 5], backs=[1, 2])
    d2 = DltCombination(fronts=[2, 3, 4, 5, 6], backs=[1, 2])
    assert score_dlt_combination(d1, front_freq, back_freq) > score_dlt_combination(d2, front_freq, back_freq)


# ---------------------------------------------------------------------------
# 震荡推荐：组合形状、取值范围、号码继承率
# ---------------------------------------------------------------------------


def test_ssq_shock_combination_shape_and_range():
    mains = [
        SsqCombination(reds=[1, 5, 10, 15, 20, 25], blue=3),
        SsqCombination(reds=[1, 5, 12, 18, 22, 28], blue=7),
        SsqCombination(reds=[1, 5, 10, 16, 24, 30], blue=3),
    ]
    red_probs = {i: 1.0 / 33 for i in range(1, 34)}
    blue_probs = {i: 1.0 / 16 for i in range(1, 17)}

    shock = generate_ssq_shock_combination(
        main_combinations=mains,
        red_probs=red_probs,
        blue_probs=blue_probs,
        red_range=range(1, 34),
        blue_range=range(1, 17),
        rng=random.Random(42),
    )

    assert len(shock.reds) == 6
    assert len(set(shock.reds)) == 6
    assert all(1 <= r <= 33 for r in shock.reds)
    assert 1 <= shock.blue <= 16
    assert shock.reds == sorted(shock.reds)


def test_ssq_shock_inherits_some_main_numbers():
    """主推荐里高频出现的号码应有较大概率被震荡继承。"""
    mains = [
        SsqCombination(reds=[1, 2, 3, 4, 5, 6], blue=10),
        SsqCombination(reds=[1, 2, 3, 4, 5, 7], blue=10),
        SsqCombination(reds=[1, 2, 3, 4, 5, 8], blue=10),
    ]
    main_reds = {1, 2, 3, 4, 5, 6, 7, 8}
    red_probs = {i: 1.0 / 33 for i in range(1, 34)}
    blue_probs = {i: 1.0 / 16 for i in range(1, 17)}

    inherited_runs = 0
    for s in range(30):
        shock = generate_ssq_shock_combination(
            main_combinations=mains,
            red_probs=red_probs,
            blue_probs=blue_probs,
            red_range=range(1, 34),
            blue_range=range(1, 17),
            keep_reds=3,
            rng=random.Random(s),
        )
        # 至少应继承 1 个主推荐号码
        if len(set(shock.reds) & main_reds) >= 1:
            inherited_runs += 1
    # 30 次里几乎都应该有继承
    assert inherited_runs >= 25


def test_dlt_shock_combination_shape_and_range():
    mains = [
        DltCombination(fronts=[1, 5, 10, 15, 20], backs=[3, 7]),
        DltCombination(fronts=[2, 5, 12, 18, 22], backs=[3, 9]),
    ]
    front_probs = {i: 1.0 / 35 for i in range(1, 36)}
    back_probs = {i: 1.0 / 12 for i in range(1, 13)}

    shock = generate_dlt_shock_combination(
        main_combinations=mains,
        front_probs=front_probs,
        back_probs=back_probs,
        front_range=range(1, 36),
        back_range=range(1, 13),
        rng=random.Random(7),
    )

    assert len(shock.fronts) == 5
    assert len(set(shock.fronts)) == 5
    assert all(1 <= f <= 35 for f in shock.fronts)
    assert len(shock.backs) == 2
    assert len(set(shock.backs)) == 2
    assert all(1 <= b <= 12 for b in shock.backs)
    assert shock.fronts == sorted(shock.fronts)
    assert shock.backs == sorted(shock.backs)


def test_shock_combination_not_identical_to_main():
    """震荡推荐应当与主推荐有差异，不能照抄。"""
    mains = [
        SsqCombination(reds=[1, 2, 3, 4, 5, 6], blue=1),
    ]
    red_probs = {i: 1.0 / 33 for i in range(1, 34)}
    blue_probs = {i: 1.0 / 16 for i in range(1, 17)}

    different = 0
    for s in range(20):
        shock = generate_ssq_shock_combination(
            main_combinations=mains,
            red_probs=red_probs,
            blue_probs=blue_probs,
            red_range=range(1, 34),
            blue_range=range(1, 17),
            rng=random.Random(s),
        )
        if set(shock.reds) != {1, 2, 3, 4, 5, 6}:
            different += 1
    # 由于补全位从「未出现号码」里抽，几乎所有次都该不同
    assert different >= 18


# ---------------------------------------------------------------------------
# 无规律震荡：基于主推荐 #1 随机替换 N 个号码
# ---------------------------------------------------------------------------


def test_ssq_random_shock_replaces_exactly_perturb_count():
    """红球应替换正好 2 个，其余 4 个保持，蓝球不变。"""
    base = SsqCombination(reds=[1, 2, 3, 4, 5, 6], blue=9)
    shock = generate_ssq_random_shock_combination(
        base_combination=base,
        red_range=range(1, 34),
        blue_range=range(1, 17),
        perturb_count=2,
        rng=random.Random(0),
    )
    assert len(shock.reds) == 6
    assert len(set(shock.reds)) == 6
    assert all(1 <= r <= 33 for r in shock.reds)
    assert shock.blue == 9  # 蓝球保持
    # 与原注的交集应为 4 个（替换了 2 个）
    common = set(shock.reds) & set(base.reds)
    assert len(common) == 4
    # 新加入的 2 个号码必须不在原注里
    new_nums = set(shock.reds) - set(base.reds)
    assert len(new_nums) == 2
    assert all(n not in base.reds for n in new_nums)


def test_dlt_random_shock_replaces_exactly_perturb_count():
    base = DltCombination(fronts=[1, 2, 3, 4, 5], backs=[3, 7])
    shock = generate_dlt_random_shock_combination(
        base_combination=base,
        front_range=range(1, 36),
        back_range=range(1, 13),
        perturb_count=2,
        rng=random.Random(0),
    )
    assert len(shock.fronts) == 5
    assert len(set(shock.fronts)) == 5
    assert shock.backs == [3, 7]  # 后区保持
    common = set(shock.fronts) & set(base.fronts)
    assert len(common) == 3
    new_nums = set(shock.fronts) - set(base.fronts)
    assert len(new_nums) == 2


def test_ssq_random_shock_is_uniform_random():
    """无规律震荡应当近似均匀分布，不依赖任何统计权重。

    在主推荐固定的情况下，从「剩余 27 个红球」中均匀随机抽 2 个，
    多次运行后被选中的号码应当较为分散。
    """
    base = SsqCombination(reds=[1, 2, 3, 4, 5, 6], blue=10)
    picked_nums = set()
    for s in range(200):
        shock = generate_ssq_random_shock_combination(
            base_combination=base,
            red_range=range(1, 34),
            blue_range=range(1, 17),
            perturb_count=2,
            rng=random.Random(s),
        )
        new_nums = set(shock.reds) - set(base.reds)
        picked_nums.update(new_nums)
    # 池中共 27 个可选号码（7-33），200 次抽样至少应触达 20 个
    assert len(picked_nums) >= 20


def test_random_shock_perturb_count_zero_returns_same():
    """perturb_count=0 时应当返回与原注号码相同的组合。"""
    base = SsqCombination(reds=[1, 5, 10, 15, 20, 25], blue=7)
    shock = generate_ssq_random_shock_combination(
        base_combination=base,
        red_range=range(1, 34),
        blue_range=range(1, 17),
        perturb_count=0,
        rng=random.Random(0),
    )
    assert set(shock.reds) == set(base.reds)
    assert shock.blue == base.blue


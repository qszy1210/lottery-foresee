"""验证 predict_service 在主推荐之后追加一注 kind=shock 的震荡推荐。"""
from __future__ import annotations

import pytest

from app.services.predict_service import recommend_ssq, recommend_dlt


@pytest.mark.parametrize("recommend_count", [1, 3, 5, 10])
def test_recommend_ssq_appends_shock_and_random_shock(recommend_count: int):
    recs = recommend_ssq(
        recommend_count=recommend_count,
        sample_size=2000,
        seed=123,
    )
    # 主推荐 N 组 + 震荡 1 注 + 无规律震荡 1 注
    assert len(recs) == recommend_count + 2
    mains = [r for r in recs if r.kind == "main"]
    shocks = [r for r in recs if r.kind == "shock"]
    randoms = [r for r in recs if r.kind == "random_shock"]
    assert len(mains) == recommend_count
    assert len(shocks) == 1
    assert len(randoms) == 1
    # 排序：先主推荐，再 shock，再 random_shock
    assert recs[-2].kind == "shock"
    assert recs[-1].kind == "random_shock"

    shock = shocks[0]
    assert len(shock.reds) == 6 and 1 <= shock.blue <= 16

    rs = randoms[0]
    assert len(rs.reds) == 6
    assert len(set(rs.reds)) == 6
    assert all(1 <= r <= 33 for r in rs.reds)
    assert 1 <= rs.blue <= 16


@pytest.mark.parametrize("recommend_count", [1, 3, 5, 10])
def test_recommend_dlt_appends_shock_and_random_shock(recommend_count: int):
    recs = recommend_dlt(
        recommend_count=recommend_count,
        sample_size=2000,
        seed=123,
    )
    assert len(recs) == recommend_count + 2
    mains = [r for r in recs if r.kind == "main"]
    shocks = [r for r in recs if r.kind == "shock"]
    randoms = [r for r in recs if r.kind == "random_shock"]
    assert len(mains) == recommend_count
    assert len(shocks) == 1
    assert len(randoms) == 1
    assert recs[-2].kind == "shock"
    assert recs[-1].kind == "random_shock"

    rs = randoms[0]
    assert len(rs.fronts) == 5 and len(set(rs.fronts)) == 5
    assert len(rs.backs) == 2 and len(set(rs.backs)) == 2


def test_random_shock_is_based_on_main_top_one_ssq():
    """无规律震荡必须基于主推荐 #1：与之共享 (6 - perturb_count)=4 个红球，且蓝球一致。"""
    recs = recommend_ssq(recommend_count=3, sample_size=2000, seed=42)
    main_top = next(r for r in recs if r.kind == "main")  # 第一个 main 就是 #1
    rs = next(r for r in recs if r.kind == "random_shock")
    common_reds = set(rs.reds) & set(main_top.reds)
    assert len(common_reds) == 4  # 替换了 2 个
    assert rs.blue == main_top.blue


def test_random_shock_is_based_on_main_top_one_dlt():
    recs = recommend_dlt(recommend_count=3, sample_size=2000, seed=42)
    main_top = next(r for r in recs if r.kind == "main")
    rs = next(r for r in recs if r.kind == "random_shock")
    common_fronts = set(rs.fronts) & set(main_top.fronts)
    assert len(common_fronts) == 3  # 5 个里替换了 2 个
    assert rs.backs == main_top.backs


def test_recommend_ssq_include_shock_false_skips_shock_only():
    """include_shock=False 仅跳过 shock，random_shock 仍保留。"""
    recs = recommend_ssq(recommend_count=3, sample_size=2000, seed=1, include_shock=False)
    assert len(recs) == 4  # 3 + 0 shock + 1 random_shock
    assert all(r.kind in ("main", "random_shock") for r in recs)
    assert sum(1 for r in recs if r.kind == "random_shock") == 1


def test_recommend_dlt_include_random_shock_false_skips_only_random_shock():
    recs = recommend_dlt(
        recommend_count=3, sample_size=2000, seed=1,
        include_shock=True, include_random_shock=False,
    )
    assert len(recs) == 4  # 3 + 1 shock + 0 random_shock
    assert sum(1 for r in recs if r.kind == "shock") == 1
    assert sum(1 for r in recs if r.kind == "random_shock") == 0


def test_recommend_ssq_disable_both_shocks_returns_only_main():
    recs = recommend_ssq(
        recommend_count=3, sample_size=2000, seed=1,
        include_shock=False, include_random_shock=False,
    )
    assert len(recs) == 3
    assert all(r.kind == "main" for r in recs)

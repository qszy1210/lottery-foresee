"""验证 predict_service 在主推荐之后追加一注 kind=shock 的震荡推荐。"""
from __future__ import annotations

import pytest

from app.services.predict_service import recommend_ssq, recommend_dlt


@pytest.mark.parametrize("recommend_count", [1, 3, 5, 10])
def test_recommend_ssq_appends_shock(recommend_count: int):
    recs = recommend_ssq(
        recommend_count=recommend_count,
        sample_size=2000,
        seed=123,
    )
    # 主推荐 N 组 + 震荡 1 注
    assert len(recs) == recommend_count + 1
    mains = [r for r in recs if r.kind == "main"]
    shocks = [r for r in recs if r.kind == "shock"]
    assert len(mains) == recommend_count
    assert len(shocks) == 1
    # 震荡注必须在列表末尾
    assert recs[-1].kind == "shock"

    shock = shocks[0]
    assert len(shock.reds) == 6
    assert len(set(shock.reds)) == 6
    assert all(1 <= r <= 33 for r in shock.reds)
    assert 1 <= shock.blue <= 16


@pytest.mark.parametrize("recommend_count", [1, 3, 5, 10])
def test_recommend_dlt_appends_shock(recommend_count: int):
    recs = recommend_dlt(
        recommend_count=recommend_count,
        sample_size=2000,
        seed=123,
    )
    assert len(recs) == recommend_count + 1
    mains = [r for r in recs if r.kind == "main"]
    shocks = [r for r in recs if r.kind == "shock"]
    assert len(mains) == recommend_count
    assert len(shocks) == 1
    assert recs[-1].kind == "shock"

    shock = shocks[0]
    assert len(shock.fronts) == 5
    assert len(set(shock.fronts)) == 5
    assert all(1 <= f <= 35 for f in shock.fronts)
    assert len(shock.backs) == 2
    assert len(set(shock.backs)) == 2
    assert all(1 <= b <= 12 for b in shock.backs)


def test_recommend_ssq_include_shock_false_skips_shock():
    recs = recommend_ssq(recommend_count=3, sample_size=2000, seed=1, include_shock=False)
    assert len(recs) == 3
    assert all(r.kind == "main" for r in recs)


def test_recommend_dlt_include_shock_false_skips_shock():
    recs = recommend_dlt(recommend_count=3, sample_size=2000, seed=1, include_shock=False)
    assert len(recs) == 3
    assert all(r.kind == "main" for r in recs)

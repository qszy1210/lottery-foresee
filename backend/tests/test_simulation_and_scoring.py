from app.domain.models import SsqCombination, DltCombination
from app.domain.scoring import score_ssq_combination, score_dlt_combination
from app.domain.stats import FrequencyStats
from app.domain.simulation import generate_ssq_candidates, generate_dlt_candidates


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


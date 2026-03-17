from app.domain.models import SsqDraw, DltDraw
from app.domain.stats import ssq_frequency, dlt_frequency, ssq_omission, dlt_omission


def test_ssq_frequency_and_omission_basic():
    draws = [
        SsqDraw(issue="1", draw_date=None, reds=[1, 2, 3, 4, 5, 6], blue=7),
        SsqDraw(issue="2", draw_date=None, reds=[1, 2, 3, 4, 5, 8], blue=9),
    ]
    red_freq, blue_freq = ssq_frequency(draws)
    assert red_freq.counts[1] == 2
    assert blue_freq.counts[7] == 1
    red_omit, blue_omit = ssq_omission(draws, range(1, 10), range(1, 12))
    assert red_omit.omissions[1] == 0
    assert blue_omit.omissions[7] == 1


def test_dlt_frequency_and_omission_basic():
    draws = [
        DltDraw(issue="1", draw_date=None, fronts=[1, 2, 3, 4, 5], backs=[1, 2]),
        DltDraw(issue="2", draw_date=None, fronts=[1, 2, 6, 7, 8], backs=[2, 3]),
    ]
    front_freq, back_freq = dlt_frequency(draws)
    assert front_freq.counts[1] == 2
    assert back_freq.counts[2] == 2
    front_omit, back_omit = dlt_omission(draws, range(1, 10), range(1, 5))
    assert front_omit.omissions[1] == 0
    assert back_omit.omissions[1] == 1


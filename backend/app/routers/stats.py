from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.stats_service import (
    NumberStat as DomainNumberStat,
    SsqStatsSummary as DomainSsqStatsSummary,
    DltStatsSummary as DomainDltStatsSummary,
    get_ssq_stats_summary,
    get_dlt_stats_summary,
)


class NumberStat(BaseModel):
    number: int
    count: int
    probability: float
    omission: int


class SsqStatsSummary(BaseModel):
    total_draws: int
    reds: List[NumberStat]
    blues: List[NumberStat]


class DltStatsSummary(BaseModel):
    total_draws: int
    fronts: List[NumberStat]
    backs: List[NumberStat]


router = APIRouter()


@router.get("/ssq/stats/summary", response_model=SsqStatsSummary)
def ssq_stats_summary() -> SsqStatsSummary:
    s: DomainSsqStatsSummary = get_ssq_stats_summary()
    return SsqStatsSummary(
        total_draws=s.total_draws,
        reds=[NumberStat(**ns.__dict__) for ns in s.reds],
        blues=[NumberStat(**ns.__dict__) for ns in s.blues],
    )


@router.get("/dlt/stats/summary", response_model=DltStatsSummary)
def dlt_stats_summary() -> DltStatsSummary:
    s: DomainDltStatsSummary = get_dlt_stats_summary()
    return DltStatsSummary(
        total_draws=s.total_draws,
        fronts=[NumberStat(**ns.__dict__) for ns in s.fronts],
        backs=[NumberStat(**ns.__dict__) for ns in s.backs],
    )


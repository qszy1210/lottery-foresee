from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Query

from app.services.predict_service import (
    SsqRecommendation,
    DltRecommendation,
    recommend_ssq,
    recommend_dlt,
)
from app.services.history_service import append_ssq, append_dlt, list_ssq, list_dlt
from app.services.schedule_service import get_next_issue_info

router = APIRouter()


def _ssq_to_dict(r: SsqRecommendation) -> dict:
    return {"reds": r.reds, "blue": r.blue, "score": r.score, "kind": r.kind}


def _dlt_to_dict(r: DltRecommendation) -> dict:
    return {"fronts": r.fronts, "backs": r.backs, "score": r.score, "kind": r.kind}


@router.post("/ssq/predict", response_model=List[SsqRecommendation])
def ssq_predict(
    window_size: Optional[int] = Query(None, ge=10),
    sample_size: Optional[int] = Query(None, ge=1000),
    recommend_count: Optional[int] = Query(None, ge=1, le=20),
    seed: Optional[int] = Query(None),
    use_correction: Optional[bool] = Query(False),
) -> List[SsqRecommendation]:
    next_info = get_next_issue_info("ssq")
    result = recommend_ssq(
        window_size=window_size,
        sample_size=sample_size,
        recommend_count=recommend_count,
        seed=seed,
        use_correction=use_correction or False,
    )
    params = {"window_size": window_size, "sample_size": sample_size, "recommend_count": recommend_count, "seed": seed}
    append_ssq(
        params,
        [_ssq_to_dict(r) for r in result],
        target_issue=next_info.issue,
        target_date=next_info.draw_date.isoformat(),
    )
    return result


@router.post("/dlt/predict", response_model=List[DltRecommendation])
def dlt_predict(
    window_size: Optional[int] = Query(None, ge=10),
    sample_size: Optional[int] = Query(None, ge=1000),
    recommend_count: Optional[int] = Query(None, ge=1, le=20),
    seed: Optional[int] = Query(None),
    use_correction: Optional[bool] = Query(False),
) -> List[DltRecommendation]:
    next_info = get_next_issue_info("dlt")
    result = recommend_dlt(
        window_size=window_size,
        sample_size=sample_size,
        recommend_count=recommend_count,
        seed=seed,
        use_correction=use_correction or False,
    )
    params = {"window_size": window_size, "sample_size": sample_size, "recommend_count": recommend_count, "seed": seed}
    append_dlt(
        params,
        [_dlt_to_dict(r) for r in result],
        target_issue=next_info.issue,
        target_date=next_info.draw_date.isoformat(),
    )
    return result


@router.get("/ssq/history")
def ssq_history(limit: Optional[int] = Query(None, ge=1, le=100)) -> List[dict]:
    return list_ssq(limit=limit or 50)


@router.get("/dlt/history")
def dlt_history(limit: Optional[int] = Query(None, ge=1, le=100)) -> List[dict]:
    return list_dlt(limit=limit or 50)


from __future__ import annotations

from fastapi import APIRouter

from app.services.schedule_service import get_next_issue_info

router = APIRouter()


@router.get("/ssq/next")
def ssq_next() -> dict:
    info = get_next_issue_info("ssq")
    return {"issue": info.issue, "draw_date": info.draw_date.isoformat()}


@router.get("/dlt/next")
def dlt_next() -> dict:
    info = get_next_issue_info("dlt")
    return {"issue": info.issue, "draw_date": info.draw_date.isoformat()}


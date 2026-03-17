"""数据拉取、比对等接口。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.compare_service import compare_ssq, compare_dlt
from app.services.fetch_state_service import should_fetch, set_last_fetch_at

router = APIRouter()


@router.post("/data/fetch-ssq")
def fetch_ssq() -> dict:
    try:
        from app.scripts.fetch_ssq import fetch_ssq_history
        fetch_ssq_history()
        from datetime import datetime, timezone
        set_last_fetch_at("ssq", datetime.now(tz=timezone.utc))
        return {"ok": True, "message": "双色球历史数据拉取成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data/fetch-dlt")
def fetch_dlt() -> dict:
    try:
        from app.scripts.fetch_dlt import fetch_dlt_history
        fetch_dlt_history()
        from datetime import datetime, timezone
        set_last_fetch_at("dlt", datetime.now(tz=timezone.utc))
        return {"ok": True, "message": "大乐透历史数据拉取成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data/ensure-fresh/{lottery}")
def ensure_fresh(lottery: str) -> dict:
    """按上次拉取时间判断是否需要拉取；需要则自动拉取。"""
    try:
        if lottery not in ("ssq", "dlt"):
            raise HTTPException(status_code=400, detail="invalid lottery")
        if not should_fetch(lottery):  # type: ignore[arg-type]
            return {"ok": True, "fetched": False, "message": "数据仍然新鲜，无需拉取"}
        if lottery == "ssq":
            from app.scripts.fetch_ssq import fetch_ssq_history
            fetch_ssq_history()
        else:
            from app.scripts.fetch_dlt import fetch_dlt_history
            fetch_dlt_history()
        from datetime import datetime, timezone
        set_last_fetch_at(lottery, datetime.now(tz=timezone.utc))  # type: ignore[arg-type]
        return {"ok": True, "fetched": True, "message": "已自动拉取最新数据"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data/compare")
def run_compare() -> dict:
    """执行预测与真实开奖比对，返回双色球与大乐透的汇总。"""
    try:
        ssq_details, ssq_summary = compare_ssq()
        dlt_details, dlt_summary = compare_dlt()
        return {"ok": True, "ssq": ssq_summary, "dlt": dlt_summary, "details": {"ssq": ssq_details, "dlt": dlt_details}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ssq/hit-stats")
def ssq_hit_stats() -> dict:
    _, summary = compare_ssq()
    return summary


@router.get("/dlt/hit-stats")
def dlt_hit_stats() -> dict:
    _, summary = compare_dlt()
    return summary

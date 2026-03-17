"""预测与真实开奖比对、命中统计；供修正权重使用。"""
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Tuple

from app.domain.models import SsqDraw, DltDraw
from app.services.data_service import load_ssq_history, load_dlt_history
from app.services.history_service import _read_list, SSQ_HISTORY_FILE, DLT_HISTORY_FILE


def _parse_created_at(created_at: str):
    try:
        return datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()
    except Exception:
        return None


def _find_target_draw_ssq(draws: List[SsqDraw], record_date: date) -> SsqDraw | None:
    """取 record 生成日期之后最近一期开奖（按 draw_date 升序，取第一条 >= record_date）。"""
    for d in sorted(draws, key=lambda x: x.draw_date):
        if d.draw_date >= record_date:
            return d
    return None


def _find_target_draw_dlt(draws: List[DltDraw], record_date: date) -> DltDraw | None:
    for d in sorted(draws, key=lambda x: x.draw_date):
        if d.draw_date >= record_date:
            return d
    return None


def compare_ssq() -> Tuple[List[dict], dict]:
    """比对双色球：每条历史预测匹配一期真实开奖，计算命中。返回 (明细, 汇总)。"""
    records = _read_list(SSQ_HISTORY_FILE)
    draws = load_ssq_history()
    if not draws:
        return [], {"total_compared": 0, "avg_red_hits": 0.0, "avg_blue_hits": 0.0}
    details = []
    red_hits_sum = 0
    blue_hits_sum = 0
    total_results = 0
    draw_by_issue = {d.issue: d for d in draws}
    for rec in records:
        target_issue = rec.get("target_issue")
        created_at = rec.get("created_at")
        target = draw_by_issue.get(str(target_issue)) if target_issue else None
        if not target:
            if not created_at:
                continue
            rd = _parse_created_at(created_at)
            if not rd:
                continue
            target = _find_target_draw_ssq(draws, rd)
        if not target:
            continue
        results = rec.get("results") or []
        for r in results:
            reds = set(r.get("reds") or [])
            blue = r.get("blue")
            hit_reds = len(reds & set(target.reds))
            hit_blue = 1 if blue == target.blue else 0
            red_hits_sum += hit_reds
            blue_hits_sum += hit_blue
            total_results += 1
            details.append(
                {
                    "record_id": rec.get("id"),
                    "target_issue": target_issue,
                    "issue": target.issue,
                    "draw_date": target.draw_date.isoformat(),
                    "hit_reds": hit_reds,
                    "hit_blue": hit_blue,
                }
            )
    avg_red = red_hits_sum / total_results if total_results else 0.0
    avg_blue = blue_hits_sum / total_results if total_results else 0.0
    summary = {"total_compared": total_results, "avg_red_hits": round(avg_red, 4), "avg_blue_hits": round(avg_blue, 4)}
    return details, summary


def compare_dlt() -> Tuple[List[dict], dict]:
    records = _read_list(DLT_HISTORY_FILE)
    draws = load_dlt_history()
    if not draws:
        return [], {"total_compared": 0, "avg_front_hits": 0.0, "avg_back_hits": 0.0}
    details = []
    front_sum = 0
    back_sum = 0
    total_results = 0
    draw_by_issue = {d.issue: d for d in draws}
    for rec in records:
        target_issue = rec.get("target_issue")
        created_at = rec.get("created_at")
        target = draw_by_issue.get(str(target_issue)) if target_issue else None
        if not target:
            if not created_at:
                continue
            rd = _parse_created_at(created_at)
            if not rd:
                continue
            target = _find_target_draw_dlt(draws, rd)
        if not target:
            continue
        results = rec.get("results") or []
        for r in results:
            fronts = set(r.get("fronts") or [])
            backs = set(r.get("backs") or [])
            hit_f = len(fronts & set(target.fronts))
            hit_b = len(backs & set(target.backs))
            front_sum += hit_f
            back_sum += hit_b
            total_results += 1
            details.append(
                {
                    "record_id": rec.get("id"),
                    "target_issue": target_issue,
                    "issue": target.issue,
                    "draw_date": target.draw_date.isoformat(),
                    "hit_fronts": hit_f,
                    "hit_backs": hit_b,
                }
            )
    n = total_results or 1
    summary = {
        "total_compared": total_results,
        "avg_front_hits": round(front_sum / n, 4),
        "avg_back_hits": round(back_sum / n, 4),
    }
    return details, summary


def get_ssq_correction_weights() -> Tuple[Dict[int, float], Dict[int, float]]:
    """根据比对结果返回红球、蓝球的修正系数（默认 1.0，无数据时全部 1.0）。"""
    _, summary = compare_ssq()
    if summary["total_compared"] < 5:
        return {}, {}
    # 简单策略：暂不按号码细分，仅返回空表示不修正；后续可按 per_number 统计再算系数
    return {}, {}


def get_dlt_correction_weights() -> Tuple[Dict[int, float], Dict[int, float]]:
    _, summary = compare_dlt()
    if summary["total_compared"] < 5:
        return {}, {}
    return {}, {}

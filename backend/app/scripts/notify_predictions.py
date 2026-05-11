"""定时拉取彩票数据 → 生成推荐 → 推送到飞书机器人。

核心策略：
- 双色球（SSQ）开奖：周二、周四、周日（Python weekday: 1, 3, 6）
- 大乐透（DLT）开奖：周一、周三、周六（Python weekday: 0, 2, 5）
- 在开奖日当天上午运行（北京时间 10:00 = UTC 02:00），生成本期推荐发送

环境变量：
- FEISHU_WEBHOOK_URL（必填）
- FEISHU_WEBHOOK_SECRET（启用签名校验时必填）
- LOTTERY_TYPE：可选，强制指定 ssq / dlt / both / auto（默认 auto）
- RECOMMEND_COUNT：每次推荐组数（默认 5）
- WINDOW_SIZE / SAMPLE_SIZE / SEED：模型参数（可选）

退出码：
- 0 成功（含「今天没有开奖，跳过」的正常退出）
- 1 失败（数据/网络/飞书任意环节出错）
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date
from typing import List, Optional

logger = logging.getLogger("notify_predictions")


# 周几对应彩种（Python weekday: 周一=0 ... 周日=6）
_SSQ_DRAW_WEEKDAYS = {1, 3, 6}  # 二 / 四 / 日
_DLT_DRAW_WEEKDAYS = {0, 2, 5}  # 一 / 三 / 六


def _decide_lotteries(today: date, override: str = "auto") -> List[str]:
    """决定今天该推送哪些彩种。

    - ssq / dlt：仅推该彩种
    - both：双色球 + 大乐透
    - auto（默认）：每天都推送 SSQ 和 DLT 两组预测，
      利用「提前公布」覆盖最近的下一期开奖（双色球与大乐透交错的开奖周期使得每天预测都可指向最近的下一期）
    - draw_day：仅在该彩种当天开奖时推送（旧版 auto 行为，可作为可选模式）
    """
    override = (override or "auto").lower()
    if override in ("ssq", "dlt"):
        return [override]
    if override in ("both", "auto"):
        return ["ssq", "dlt"]
    if override == "draw_day":
        wd = today.weekday()
        out: List[str] = []
        if wd in _DLT_DRAW_WEEKDAYS:
            out.append("dlt")
        if wd in _SSQ_DRAW_WEEKDAYS:
            out.append("ssq")
        return out
    return ["ssq", "dlt"]


def _ensure_data() -> None:
    """启动前刷新本地历史数据（增量+多源容错，失败也不影响推送）。"""
    from app.scripts.fetch_ssq import fetch_ssq_history
    from app.scripts.fetch_dlt import fetch_dlt_history
    try:
        fetch_ssq_history()
    except Exception as exc:
        logger.warning("拉取 SSQ 数据失败（将使用本地数据）: %s", exc)
    try:
        fetch_dlt_history()
    except Exception as exc:
        logger.warning("拉取 DLT 数据失败（将使用本地数据）: %s", exc)


def _send_ssq(
    webhook_url: str,
    secret: Optional[str],
    recommend_count: int,
    window_size: Optional[int],
    sample_size: Optional[int],
    seed: Optional[int],
) -> None:
    from app.services.predict_service import recommend_ssq
    from app.services.schedule_service import get_next_issue_info
    from app.services.feishu_notifier import build_ssq_card, send_card

    info = get_next_issue_info("ssq")
    recs = recommend_ssq(
        window_size=window_size,
        sample_size=sample_size,
        recommend_count=recommend_count,
        seed=seed,
    )
    payload_recs = [
        {"reds": r.reds, "blue": r.blue, "score": r.score, "kind": r.kind}
        for r in recs
    ]
    card = build_ssq_card(
        issue=info.issue,
        draw_date=info.draw_date.isoformat(),
        recommendations=payload_recs,
    )
    send_card(webhook_url, secret, card)
    logger.info("已推送 SSQ %s 期预测（%d 组）", info.issue, len(payload_recs))


def _send_dlt(
    webhook_url: str,
    secret: Optional[str],
    recommend_count: int,
    window_size: Optional[int],
    sample_size: Optional[int],
    seed: Optional[int],
) -> None:
    from app.services.predict_service import recommend_dlt
    from app.services.schedule_service import get_next_issue_info
    from app.services.feishu_notifier import build_dlt_card, send_card

    info = get_next_issue_info("dlt")
    recs = recommend_dlt(
        window_size=window_size,
        sample_size=sample_size,
        recommend_count=recommend_count,
        seed=seed,
    )
    payload_recs = [
        {"fronts": r.fronts, "backs": r.backs, "score": r.score, "kind": r.kind}
        for r in recs
    ]
    card = build_dlt_card(
        issue=info.issue,
        draw_date=info.draw_date.isoformat(),
        recommendations=payload_recs,
    )
    send_card(webhook_url, secret, card)
    logger.info("已推送 DLT %s 期预测（%d 组）", info.issue, len(payload_recs))


def _opt_int(name: str) -> Optional[int]:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="发送彩票推荐到飞书")
    parser.add_argument(
        "--lottery", default=os.environ.get("LOTTERY_TYPE", "auto"),
        choices=["auto", "ssq", "dlt", "both", "draw_day"],
        help="彩种选择：auto/both=每天双色球+大乐透；ssq/dlt=单一彩种；draw_day=仅当天开奖的彩种",
    )
    parser.add_argument("--recommend-count", type=int,
                        default=int(os.environ.get("RECOMMEND_COUNT", "5")))
    parser.add_argument("--dry-run", action="store_true",
                        help="只生成推荐不发送（调试用）")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    today = date.today()
    targets = _decide_lotteries(today, override=args.lottery)
    if not targets:
        logger.info("今天 %s（周%d）无需推送（mode=%s）",
                    today, today.weekday() + 1, args.lottery)
        return 0

    logger.info("今天将推送：%s", ", ".join(targets))

    _ensure_data()

    if args.dry_run:
        from app.services.predict_service import recommend_ssq, recommend_dlt
        from app.services.schedule_service import get_next_issue_info
        for t in targets:
            info = get_next_issue_info(t)
            if t == "ssq":
                recs = recommend_ssq(recommend_count=args.recommend_count)
                logger.info("[dry-run] SSQ 期 %s: %s", info.issue,
                            [(r.kind, r.reds, r.blue) for r in recs])
            else:
                recs = recommend_dlt(recommend_count=args.recommend_count)
                logger.info("[dry-run] DLT 期 %s: %s", info.issue,
                            [(r.kind, r.fronts, r.backs) for r in recs])
        return 0

    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL", "").strip()
    secret = (os.environ.get("FEISHU_WEBHOOK_SECRET") or "").strip() or None
    if not webhook_url:
        logger.error("缺少 FEISHU_WEBHOOK_URL 环境变量")
        return 1

    window_size = _opt_int("WINDOW_SIZE")
    sample_size = _opt_int("SAMPLE_SIZE")
    seed = _opt_int("SEED")

    failed = False
    for t in targets:
        try:
            if t == "ssq":
                _send_ssq(webhook_url, secret, args.recommend_count,
                          window_size, sample_size, seed)
            else:
                _send_dlt(webhook_url, secret, args.recommend_count,
                          window_size, sample_size, seed)
        except Exception as exc:
            logger.exception("推送 %s 失败: %s", t, exc)
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

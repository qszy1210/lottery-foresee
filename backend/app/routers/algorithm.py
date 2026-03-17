from fastapi import APIRouter

router = APIRouter()


@router.get("/algorithm")
def algorithm() -> dict:
    return {
        "summary": "基于最近 N 期历史开奖，统计各号码出现频率并归一化为概率；按该概率对号码加权，随机生成大量候选组合（蒙特卡洛）；对每个组合按「组合内号码概率之和」打分并排序，取前 K 组作为推荐。",
        "params": {
            "window_size": "统计窗口期数（默认 100）",
            "sample_size": "候选组合数量（默认 50000）",
            "recommend_count": "推荐组数（1–20）",
        },
    }

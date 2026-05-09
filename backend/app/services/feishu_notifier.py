"""飞书自定义机器人 webhook 发送器。

参考：https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
- 启用「签名校验」时，请求需带 timestamp 与 sign 字段
- sign = base64(HmacSHA256(timestamp + "\\n" + secret, ""))
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


def gen_sign(timestamp: int, secret: str) -> str:
    """根据飞书签名规则生成 sign 字段。"""
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(hmac_code).decode("utf-8")


def build_payload(
    body: Dict[str, Any],
    secret: Optional[str] = None,
    timestamp: Optional[int] = None,
) -> Dict[str, Any]:
    """构造飞书 webhook 请求体；secret 非空则附加签名字段。"""
    payload: Dict[str, Any] = dict(body)
    if secret:
        ts = timestamp if timestamp is not None else int(time.time())
        payload["timestamp"] = str(ts)
        payload["sign"] = gen_sign(ts, secret)
    return payload


def send_text(webhook_url: str, secret: Optional[str], text: str) -> Dict[str, Any]:
    body = {"msg_type": "text", "content": {"text": text}}
    return _post(webhook_url, build_payload(body, secret=secret))


def send_card(
    webhook_url: str,
    secret: Optional[str],
    card: Dict[str, Any],
) -> Dict[str, Any]:
    body = {"msg_type": "interactive", "card": card}
    return _post(webhook_url, build_payload(body, secret=secret))


def _post(webhook_url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    resp = requests.post(webhook_url, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    code = data.get("code") or data.get("StatusCode")
    if code not in (0, None):
        raise RuntimeError(
            f"飞书返回错误 code={code} msg={data.get('msg') or data.get('StatusMessage')}"
        )
    return data


# ---------------------------------------------------------------------------
# 卡片构建辅助
# ---------------------------------------------------------------------------

def _ball(num: int, color: str) -> str:
    return f"<font color='{color}'>**{num:02d}**</font>"


def _format_ssq_line(idx: int, reds: List[int], blue: int, score: float) -> str:
    red_str = " ".join(_ball(n, "red") for n in reds)
    blue_str = _ball(blue, "blue")
    return f"**#{idx}** 红 {red_str} ｜蓝 {blue_str} ｜分 {score:.4f}"


def _format_dlt_line(idx: int, fronts: List[int], backs: List[int], score: float) -> str:
    front_str = " ".join(_ball(n, "blue") for n in fronts)
    back_str = " ".join(_ball(n, "orange") for n in backs)
    return f"**#{idx}** 前 {front_str} ｜后 {back_str} ｜分 {score:.4f}"


def build_ssq_card(
    issue: str,
    draw_date: str,
    recommendations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """构造双色球推荐卡片。"""
    elements: List[Dict[str, Any]] = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"**预测期号：{issue}**　开奖日：{draw_date}\n"
                    f"基于历史数据 + 蒙特卡洛算法 ｜共 {len(recommendations)} 组推荐"
                ),
            },
        },
        {"tag": "hr"},
    ]
    for idx, rec in enumerate(recommendations, start=1):
        line = _format_ssq_line(idx, rec["reds"], rec["blue"], rec["score"])
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": line}})
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "note",
        "elements": [{
            "tag": "plain_text",
            "content": "Lottery Foresee · 仅供学习研究，理性参考",
        }],
    })
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "red",
            "title": {"tag": "plain_text", "content": "🎯 双色球推荐"},
        },
        "elements": elements,
    }


def build_dlt_card(
    issue: str,
    draw_date: str,
    recommendations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """构造大乐透推荐卡片。"""
    elements: List[Dict[str, Any]] = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": (
                    f"**预测期号：{issue}**　开奖日：{draw_date}\n"
                    f"基于历史数据 + 蒙特卡洛算法 ｜共 {len(recommendations)} 组推荐"
                ),
            },
        },
        {"tag": "hr"},
    ]
    for idx, rec in enumerate(recommendations, start=1):
        line = _format_dlt_line(idx, rec["fronts"], rec["backs"], rec["score"])
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": line}})
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "note",
        "elements": [{
            "tag": "plain_text",
            "content": "Lottery Foresee · 仅供学习研究，理性参考",
        }],
    })
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": "🎯 大乐透推荐"},
        },
        "elements": elements,
    }

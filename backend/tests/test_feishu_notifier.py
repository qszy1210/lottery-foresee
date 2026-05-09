"""飞书 webhook 发送模块测试。"""
from __future__ import annotations

import base64
import hashlib
import hmac
from unittest.mock import patch, MagicMock

import pytest

from app.services.feishu_notifier import (
    gen_sign,
    build_payload,
    send_text,
    send_card,
    build_ssq_card,
    build_dlt_card,
)


# ---------------------------------------------------------------------------
# 签名
# ---------------------------------------------------------------------------

class TestSign:
    def test_gen_sign_matches_reference(self):
        """飞书签名规范：base64(HmacSHA256(timestamp + '\\n' + secret, b''))。"""
        ts = 1700000000
        secret = "UKqA7xqQ5JoDWZOJCiLzue"
        expected_str = f"{ts}\n{secret}"
        expected = base64.b64encode(
            hmac.new(expected_str.encode("utf-8"), digestmod=hashlib.sha256).digest()
        ).decode("utf-8")
        assert gen_sign(ts, secret) == expected

    def test_sign_changes_with_secret(self):
        ts = 1700000000
        a = gen_sign(ts, "secret-a")
        b = gen_sign(ts, "secret-b")
        assert a != b

    def test_sign_changes_with_timestamp(self):
        secret = "abc"
        a = gen_sign(1700000000, secret)
        b = gen_sign(1700000001, secret)
        assert a != b


# ---------------------------------------------------------------------------
# 请求体组装
# ---------------------------------------------------------------------------

class TestBuildPayload:
    def test_payload_without_secret(self):
        body = {"msg_type": "text", "content": {"text": "hello"}}
        out = build_payload(body, secret=None)
        assert out == body
        assert "sign" not in out
        assert "timestamp" not in out

    def test_payload_with_secret(self):
        body = {"msg_type": "text", "content": {"text": "hi"}}
        out = build_payload(body, secret="key", timestamp=1700000000)
        assert out["msg_type"] == "text"
        assert out["timestamp"] == "1700000000"
        assert out["sign"] == gen_sign(1700000000, "key")


# ---------------------------------------------------------------------------
# HTTP 发送
# ---------------------------------------------------------------------------

class TestSend:
    def _ok_response(self) -> MagicMock:
        resp = MagicMock()
        resp.json.return_value = {"code": 0, "msg": "success"}
        resp.raise_for_status = MagicMock()
        return resp

    def test_send_text_posts_correct_payload(self):
        with patch("app.services.feishu_notifier.requests.post") as mock_post:
            mock_post.return_value = self._ok_response()
            send_text("https://hook", "secret", "ping")
        assert mock_post.called
        url, = mock_post.call_args.args
        kwargs = mock_post.call_args.kwargs
        assert url == "https://hook"
        payload = kwargs["json"]
        assert payload["msg_type"] == "text"
        assert payload["content"]["text"] == "ping"
        assert payload["sign"]
        assert payload["timestamp"]

    def test_send_card(self):
        card = {"header": {"title": {"tag": "plain_text", "content": "test"}}}
        with patch("app.services.feishu_notifier.requests.post") as mock_post:
            mock_post.return_value = self._ok_response()
            send_card("https://hook", None, card)
        payload = mock_post.call_args.kwargs["json"]
        assert payload["msg_type"] == "interactive"
        assert payload["card"] == card
        assert "sign" not in payload

    def test_feishu_error_code_raises(self):
        resp = MagicMock()
        resp.json.return_value = {"code": 9499, "msg": "sign verify failed"}
        resp.raise_for_status = MagicMock()
        with patch("app.services.feishu_notifier.requests.post", return_value=resp):
            with pytest.raises(RuntimeError, match="飞书返回错误"):
                send_text("https://hook", "k", "x")

    def test_http_error_raises(self):
        import requests as rq
        resp = MagicMock()
        resp.raise_for_status = MagicMock(side_effect=rq.HTTPError("500"))
        with patch("app.services.feishu_notifier.requests.post", return_value=resp):
            with pytest.raises(rq.HTTPError):
                send_text("https://hook", "k", "x")


# ---------------------------------------------------------------------------
# 卡片构造
# ---------------------------------------------------------------------------

class TestCardBuilders:
    def test_ssq_card_structure(self):
        recs = [
            {"reds": [1, 5, 10, 15, 20, 25], "blue": 7, "score": 0.36},
            {"reds": [2, 8, 12, 18, 22, 30], "blue": 3, "score": 0.35},
        ]
        card = build_ssq_card("2026033", "2026-03-26", recs)
        assert card["header"]["template"] == "red"
        assert "双色球" in card["header"]["title"]["content"]
        # header div + hr + 2 rec divs + hr + note
        assert len(card["elements"]) == 6
        first_div_content = card["elements"][0]["text"]["content"]
        assert "2026033" in first_div_content
        assert "2026-03-26" in first_div_content

    def test_dlt_card_structure(self):
        recs = [
            {"fronts": [1, 5, 10, 15, 20], "backs": [3, 7], "score": 0.42},
        ]
        card = build_dlt_card("2026031", "2026-03-25", recs)
        assert card["header"]["template"] == "blue"
        assert "大乐透" in card["header"]["title"]["content"]
        assert len(card["elements"]) >= 4

    def test_card_renders_recommendation_numbers(self):
        recs = [{"reds": [1, 2, 3, 4, 5, 6], "blue": 7, "score": 0.5}]
        card = build_ssq_card("2026001", "2026-01-01", recs)
        rendered = "\n".join(
            e.get("text", {}).get("content", "") for e in card["elements"]
            if e.get("tag") == "div"
        )
        for n in ["01", "02", "03", "04", "05", "06", "07"]:
            assert n in rendered

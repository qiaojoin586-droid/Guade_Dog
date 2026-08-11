"""讯飞开放平台通用工具: HMAC 签名与异常。

ASR(iat)与 TTS 共用的鉴权逻辑: 按 RFC3986 规则用 APISecret 对
"host / date / request-line" 做 HMAC-SHA256 签名,放入 Authorization 头。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import urlparse


class XfyunError(Exception):
    """讯飞 API 调用失败(鉴权、业务错误码、超时等)。"""


def build_auth_header(host: str, path: str, api_key: str, api_secret: str) -> tuple[str, str]:
    """构造讯飞 WebSocket 鉴权头。

    Args:
        host: 服务主机,如 iat-api.xfyun.cn
        path: 服务路径,如 /v2/iat
        api_key: XFYUN_API_KEY
        api_secret: XFYUN_API_SECRET

    Returns:
        (Authorization 头值, RFC1123 日期)——日期用于请求的 Date 头,必须与签名一致。
    """
    date = format_datetime(datetime.now(timezone.utc), usegmt=True)
    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
    digest = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature = base64.b64encode(digest).decode("utf-8")
    authorization = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    return authorization, date


def split_ws_url(url: str) -> tuple[str, str]:
    """从 wss:// URL 拆出 (host, path),供签名与 Date 头使用。"""
    parsed = urlparse(url)
    return parsed.hostname or "", parsed.path or "/"

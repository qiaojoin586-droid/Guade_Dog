"""讯飞签名工具测试。"""

import base64
import hashlib
import hmac
import re

from app.utils.xfyun import build_auth_header, split_ws_url


def test_build_auth_header_format():
    """Authorization 头应包含 api_key/algorithm/headers/signature 四要素。"""
    auth, date = build_auth_header("iat-api.xfyun.cn", "/v2/iat", "test-key", "test-secret")
    assert auth.startswith('api_key="test-key"')
    assert 'algorithm="hmac-sha256"' in auth
    assert 'headers="host date request-line"' in auth
    assert re.search(r'signature="[A-Za-z0-9+/=]+"', auth)
    # RFC1123 日期
    assert re.match(r"\w{3}, \d{2} \w{3} \d{4} \d{2}:\d{2}:\d{2} GMT", date)


def test_build_auth_header_signature_is_hmac():
    """签名应等于用 APISecret 对 host/date/request-line 的 HMAC-SHA256。"""
    host, path = "iat-api.xfyun.cn", "/v2/iat"
    secret = "my-secret"
    auth, date = build_auth_header(host, path, "k", secret)
    signature = re.search(r'signature="([A-Za-z0-9+/=]+)"', auth).group(1)

    origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
    expected = base64.b64encode(
        hmac.new(secret.encode(), origin.encode(), hashlib.sha256).digest()
    ).decode()
    assert signature == expected


def test_split_ws_url():
    assert split_ws_url("wss://iat-api.xfyun.cn/v2/iat") == ("iat-api.xfyun.cn", "/v2/iat")
    assert split_ws_url("wss://tts-api.xfyun.cn/v2/tts") == ("tts-api.xfyun.cn", "/v2/tts")

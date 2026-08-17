"""视觉服务测试：JSON 容错解析 + 错误分类（不触网）。"""

import io
import json
from types import SimpleNamespace

import httpx
import pytest
from PIL import Image

from app.agents.safety.service import vision


def _fake_settings(key: str = "sk-test") -> SimpleNamespace:
    return SimpleNamespace(DASHSCOPE_API_KEY=key, DASHSCOPE_VISION_MODEL="qwen-vl-max")


def _tiny_jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buf, format="JPEG")
    return buf.getvalue()


# ===== _extract_json 容错解析 =====

def test_extract_json_plain():
    assert vision._extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_fenced():
    assert vision._extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_with_surrounding_text():
    assert vision._extract_json('识别结果如下：{"a": 1} 完毕') == {"a": 1}


def test_extract_json_invalid_raises():
    with pytest.raises(json.JSONDecodeError):
        vision._extract_json("完全没有 JSON")


# ===== recognize_image 错误分类 =====

@pytest.mark.asyncio
async def test_recognize_missing_api_key(monkeypatch):
    """未配置 DASHSCOPE_API_KEY → 50020。"""
    monkeypatch.setattr(vision, "get_settings", lambda: _fake_settings(key=""))
    with pytest.raises(vision.VisionError) as exc_info:
        await vision.recognize_image(_tiny_jpeg(), "指令")
    assert exc_info.value.code == 50020


@pytest.mark.asyncio
async def test_recognize_invalid_image_format(monkeypatch):
    """非 jpg/png → 40001。"""
    monkeypatch.setattr(vision, "get_settings", lambda: _fake_settings())
    with pytest.raises(vision.VisionError) as exc_info:
        await vision.recognize_image(b"this is not an image", "指令")
    assert exc_info.value.code == 40001


@pytest.mark.asyncio
async def test_recognize_quota_error_maps_50020(monkeypatch):
    """额度耗尽（AllocationQuota）→ 50020。"""

    monkeypatch.setattr(vision, "get_settings", lambda: _fake_settings())

    class FakeResponse:
        status_code = 429
        text = '{"error":{"code":"AllocationQuota.FreeTierOnly","message":"quota"}}'

        def raise_for_status(self):
            raise httpx.HTTPStatusError(
                "429",
                request=httpx.Request("POST", vision.DASHSCOPE_COMPAT_URL),
                response=self,
            )

    class FakeClient:
        async def post(self, *args, **kwargs):
            return FakeResponse()

    class FakeContextManager:
        async def __aenter__(self):
            return FakeClient()

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(vision.httpx, "AsyncClient", lambda **kw: FakeContextManager())

    with pytest.raises(vision.VisionError) as exc_info:
        await vision.recognize_image(_tiny_jpeg(), "指令")
    assert exc_info.value.code == 50020


@pytest.mark.asyncio
async def test_recognize_content_list_without_text_maps_40200(monkeypatch):
    """content 为分段列表但无文本段（omni 类返回）→ 40200 而非裸 500。"""

    monkeypatch.setattr(vision, "get_settings", lambda: _fake_settings())

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": [{"type": "audio", "audio": "xx"}]}}]}

    class FakeClient:
        async def post(self, *args, **kwargs):
            return FakeResponse()

    class FakeContextManager:
        async def __aenter__(self):
            return FakeClient()

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(vision.httpx, "AsyncClient", lambda **kw: FakeContextManager())

    with pytest.raises(vision.VisionError) as exc_info:
        await vision.recognize_image(_tiny_jpeg(), "指令")
    assert exc_info.value.code == 40200


@pytest.mark.asyncio
async def test_recognize_content_list_with_text_ok(monkeypatch):
    """content 为分段列表且含 text 段 → 正常拼接并解析 JSON。"""

    monkeypatch.setattr(vision, "get_settings", lambda: _fake_settings())

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": [{"type": "text", "text": "{\"a\": 1}"}]}}]}

    class FakeClient:
        async def post(self, *args, **kwargs):
            return FakeResponse()

    class FakeContextManager:
        async def __aenter__(self):
            return FakeClient()

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(vision.httpx, "AsyncClient", lambda **kw: FakeContextManager())

    result = await vision.recognize_image(_tiny_jpeg(), "指令")
    assert result == {"a": 1}


@pytest.mark.asyncio
async def test_recognize_http_error_maps_50020(monkeypatch):
    """HTTP 5xx → 50020。"""

    monkeypatch.setattr(vision, "get_settings", lambda: _fake_settings())

    class FakeResponse:
        status_code = 500
        text = "internal error"

        def raise_for_status(self):
            raise httpx.HTTPStatusError(
                "500",
                request=httpx.Request("POST", vision.DASHSCOPE_COMPAT_URL),
                response=self,
            )

    class FakeClient:
        async def post(self, *args, **kwargs):
            return FakeResponse()

    class FakeContextManager:
        async def __aenter__(self):
            return FakeClient()

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(vision.httpx, "AsyncClient", lambda **kw: FakeContextManager())

    with pytest.raises(vision.VisionError) as exc_info:
        await vision.recognize_image(_tiny_jpeg(), "指令")
    assert exc_info.value.code == 50020
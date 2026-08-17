"""安全模块 API 测试（mock 服务层，不触网）。"""

import httpx
import pytest

from app.agents.safety.service import medicine
from app.core import llm


@pytest.fixture
def client():
    from app.main import create_app

    app = create_app()
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_ping(client):
    r = await client.get("/api/v1/safety/ping")
    assert r.status_code == 200
    assert r.json()["data"]["module"] == "safety"


@pytest.mark.asyncio
async def test_health_ask_emergency(client):
    """紧急词命中：不需要真实 LLM，直接返回急救指引。"""
    r = await client.post("/api/v1/safety/health/ask", json={"question": "胸痛怎么办"})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["data"]["emergency"] is True
    assert "120" in body["data"]["tts_text"]


@pytest.mark.asyncio
async def test_health_ask_llm_failure_returns_503(client, monkeypatch):
    """LLM 失败 → 503 / 50021。"""

    async def fail(*args, **kwargs):
        raise llm.LLMError("boom")

    monkeypatch.setattr(llm, "complete", fail)
    r = await client.post("/api/v1/safety/health/ask", json={"question": "感冒了怎么办"})
    assert r.status_code == 503
    assert r.json()["code"] == 50021


@pytest.mark.asyncio
async def test_health_ask_empty_question_422(client):
    r = await client.post("/api/v1/safety/health/ask", json={"question": ""})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_health_ask_whitespace_question_422(client):
    """纯空白问题 → 422 校验失败，而不是 503 网络繁忙。"""
    r = await client.post("/api/v1/safety/health/ask", json={"question": "   "})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_medicine_recognize_success(client, monkeypatch):
    """mock 药品识别成功路径。"""

    async def fake_recognize(image_bytes):
        return {
            "medicine": {
                "name": "阿莫西林胶囊",
                "category": "青霉素类抗生素",
                "indications": "呼吸道感染",
                "dosage": "一次0.5g",
                "precautions": "青霉素过敏者禁用",
            },
            "unknown_fields": [],
            "tts_text": "识别到阿莫西林胶囊，用于呼吸道感染。以上为AI识别结果，仅供参考，请以说明书和医嘱为准",
        }

    monkeypatch.setattr(medicine, "recognize", fake_recognize)
    files = {"image": ("test.jpg", b"\xff\xd8\xff fake", "image/jpeg")}
    r = await client.post("/api/v1/safety/medicine/recognize", files=files)
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["data"]["medicine"]["name"] == "阿莫西林胶囊"
    assert "仅供参考" in body["data"]["tts_text"]


@pytest.mark.asyncio
async def test_currency_recognize_missing_image_422(client):
    """缺图片字段 → FastAPI 422。"""
    r = await client.post("/api/v1/safety/currency/recognize")
    assert r.status_code == 422
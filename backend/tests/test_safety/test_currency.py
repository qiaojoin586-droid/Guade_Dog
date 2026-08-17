"""钞票识别服务测试（mock 视觉层，不触网）。"""

import pytest

from app.agents.safety.service import currency


@pytest.mark.asyncio
async def test_high_confidence_returns_denomination(monkeypatch):
    """高置信度：正常播报面额。"""

    async def fake_vision(image_bytes, instruction):
        return {"denomination": "50元", "confidence": 0.92}

    monkeypatch.setattr(currency, "recognize_image", fake_vision)
    result = await currency.recognize(b"fake-image")
    assert result["currency"] == "CNY"
    assert result["amount"] == 50
    assert result["denomination"] == "50元"
    assert result["tts_text"] == "这是一张50元"


@pytest.mark.asyncio
async def test_low_confidence_does_not_report(monkeypatch):
    """置信度低于 0.7：不播报具体面额。"""

    async def fake_vision(image_bytes, instruction):
        return {"denomination": "100元", "confidence": 0.5}

    monkeypatch.setattr(currency, "recognize_image", fake_vision)
    result = await currency.recognize(b"fake-image")
    assert result["denomination"] == "unknown"
    assert result["amount"] is None
    assert result["tts_text"] == "无法确认面额，请他人协助"


@pytest.mark.asyncio
async def test_unknown_denomination_does_not_report(monkeypatch):
    """模型不确定：不播报具体面额。"""

    async def fake_vision(image_bytes, instruction):
        return {"denomination": "unknown", "confidence": 0.99}

    monkeypatch.setattr(currency, "recognize_image", fake_vision)
    result = await currency.recognize(b"fake-image")
    assert result["denomination"] == "unknown"
    assert result["amount"] is None
    assert result["tts_text"] == "无法确认面额，请他人协助"


@pytest.mark.asyncio
async def test_invalid_denomination_does_not_report(monkeypatch):
    """模型输出非法面额：不播报。"""

    async def fake_vision(image_bytes, instruction):
        return {"denomination": "3元", "confidence": 0.99}

    monkeypatch.setattr(currency, "recognize_image", fake_vision)
    result = await currency.recognize(b"fake-image")
    assert result["denomination"] == "unknown"
    assert result["tts_text"] == "无法确认面额，请他人协助"
"""药品识别服务测试（mock 视觉层，不触网）。"""

import pytest

from app.agents.safety.service import medicine
from app.agents.safety.service.vision import VisionError


@pytest.mark.asyncio
async def test_medicine_recognize_with_disclaimer(monkeypatch):
    """成功识别：返回结构化信息 + 免责声明播报。"""

    async def fake_vision(image_bytes, instruction):
        return {
            "name": "阿莫西林胶囊",
            "category": "青霉素类抗生素",
            "indications": "呼吸道感染",
            "dosage": "一次0.5g，每6~8小时1次",
            "precautions": "青霉素过敏者禁用",
        }

    monkeypatch.setattr(medicine, "recognize_image", fake_vision)
    result = await medicine.recognize(b"fake-image")
    assert result["medicine"]["name"] == "阿莫西林胶囊"
    assert result["medicine"]["category"] == "青霉素类抗生素"
    assert result["unknown_fields"] == []
    assert "识别到阿莫西林胶囊" in result["tts_text"]
    assert "以上为AI识别结果，仅供参考" in result["tts_text"]


@pytest.mark.asyncio
async def test_medicine_unknown_fields_not_broadcast(monkeypatch):
    """不确定字段：如实标记 unknown，播报不含该字段。"""

    async def fake_vision(image_bytes, instruction):
        return {"name": "布洛芬", "category": "unknown", "indications": "unknown", "dosage": "unknown", "precautions": "unknown"}

    monkeypatch.setattr(medicine, "recognize_image", fake_vision)
    result = await medicine.recognize(b"fake-image")
    assert set(result["unknown_fields"]) == {"category", "indications", "dosage", "precautions"}
    assert "unknown" not in result["tts_text"]
    assert "识别到布洛芬" in result["tts_text"]


@pytest.mark.asyncio
async def test_medicine_chinese_unknown_normalized(monkeypatch):
    """模型输出中文「未知」等变体：进 unknown_fields，不播报。"""

    async def fake_vision(image_bytes, instruction):
        return {"name": "布洛芬", "category": "未知", "indications": "不详", "dosage": "无法确定", "precautions": "暂无"}

    monkeypatch.setattr(medicine, "recognize_image", fake_vision)
    result = await medicine.recognize(b"fake-image")
    assert set(result["unknown_fields"]) == {"category", "indications", "dosage", "precautions"}
    assert "未知" not in result["tts_text"]
    assert "不详" not in result["tts_text"]
    assert "识别到布洛芬" in result["tts_text"]


@pytest.mark.asyncio
async def test_medicine_missing_name_raises(monkeypatch):
    """未识别到药品名 → VisionError 40200。"""

    async def fake_vision(image_bytes, instruction):
        return {"name": "unknown", "category": "unknown"}

    monkeypatch.setattr(medicine, "recognize_image", fake_vision)
    with pytest.raises(VisionError) as exc_info:
        await medicine.recognize(b"fake-image")
    assert exc_info.value.code == 40200
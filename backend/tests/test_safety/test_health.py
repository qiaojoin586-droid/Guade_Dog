"""健康问答服务测试（全部 mock，不触网）。"""

import pytest

from app.agents.safety.service import health
from app.core import llm


@pytest.mark.asyncio
async def test_emergency_keyword_intercepted_without_llm(monkeypatch):
    """紧急词命中：直接返回急救指引，不调用 LLM。"""

    async def boom(*args, **kwargs):
        raise AssertionError("紧急场景不应调用 LLM")

    monkeypatch.setattr(llm, "complete", boom)
    result = await health.ask("胸痛怎么办")
    assert result["emergency"] is True
    assert "120" in result["tts_text"]
    assert result["code"] == 40300  # ERR_EMERGENCY_INTERCEPT


@pytest.mark.asyncio
async def test_normal_question_calls_llm_with_guardrail(monkeypatch):
    """普通问题：调用 LLM 并返回回答（system 护栏必须存在）。"""

    async def fake_complete(prompt, model=None, json_mode=False, system=None, temperature=0.2):
        assert system, "健康问答必须携带护栏 system 提示词"
        return "建议多休息、多喝水；如症状持续加重请及时就医。"

    monkeypatch.setattr(llm, "complete", fake_complete)
    result = await health.ask("感冒了能吃药吗")
    assert result["emergency"] is False
    assert result["code"] == 200
    assert "建议多休息" in result["tts_text"]


@pytest.mark.asyncio
async def test_llm_failure_retries_once(monkeypatch):
    """LLM 连续失败：重试 1 次后抛 LLMError。"""

    calls = {"n": 0}

    async def fail(*args, **kwargs):
        calls["n"] += 1
        raise llm.LLMError("boom")

    monkeypatch.setattr(llm, "complete", fail)
    with pytest.raises(llm.LLMError):
        await health.ask("普通问题")
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_empty_question_raises():
    with pytest.raises(ValueError):
        await health.ask("   ")


@pytest.mark.asyncio
async def test_bus_route_120_not_emergency(monkeypatch):
    """包含裸 120 的日常问题不应命中紧急词（如 120 路公交车）。"""

    async def fake_complete(prompt, model=None, json_mode=False, system=None, temperature=0.2):
        return "120路公交在下一站换乘，请留意报站。"

    monkeypatch.setattr(llm, "complete", fake_complete)
    result = await health.ask("请问120路公交车怎么坐")
    assert result["emergency"] is False
    assert result["code"] == 200
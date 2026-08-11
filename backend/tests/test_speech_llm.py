"""LLM 供应商分发测试(不触网,只验证选择逻辑)。"""

from types import SimpleNamespace

import pytest

from app.core import llm


@pytest.mark.asyncio
async def test_complete_dispatches_to_spark(monkeypatch):
    """LLM_PROVIDER=spark → 调用 _complete_spark。"""
    called = {}

    async def fake_spark(prompt, json_mode=False, system=None, temperature=0.2):
        called["provider"] = "spark"
        return '{"tool": null}'

    monkeypatch.setattr(llm, "get_settings", lambda: SimpleNamespace(LLM_PROVIDER="spark"))
    monkeypatch.setattr(llm, "_complete_spark", fake_spark)
    assert await llm.complete("你好") == '{"tool": null}'
    assert called == {"provider": "spark"}


@pytest.mark.asyncio
async def test_complete_dispatches_to_dashscope(monkeypatch):
    """LLM_PROVIDER=dashscope → 调用 _complete_dashscope。"""
    called = {}

    async def fake_dash(prompt, model=None, json_mode=False, system=None, temperature=0.2):
        called["provider"] = "dashscope"
        return "ok"

    monkeypatch.setattr(llm, "get_settings", lambda: SimpleNamespace(LLM_PROVIDER="dashscope"))
    monkeypatch.setattr(llm, "_complete_dashscope", fake_dash)
    assert await llm.complete("你好") == "ok"
    assert called == {"provider": "dashscope"}


@pytest.mark.asyncio
async def test_complete_unknown_provider_raises(monkeypatch):
    """未知 provider → LLMError。"""
    monkeypatch.setattr(llm, "get_settings", lambda: SimpleNamespace(LLM_PROVIDER="unknown"))
    with pytest.raises(llm.LLMError):
        await llm.complete("你好")

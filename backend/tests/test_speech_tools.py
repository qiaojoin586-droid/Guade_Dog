"""工具注册表测试: 注册表完整性、占位分发、未知工具回退。"""

import pytest

from app.agents.conversation.service import tools


def test_registry_contains_planned_tools():
    """预埋的 4 个工具都应存在,且归属 Agent 模块合法。"""
    assert {
        "navigation.start",
        "safety.sos",
        "perception.weather",
        "perception.reminder",
    } <= set(tools.TOOL_REGISTRY)
    valid_modules = {"navigation", "safety", "perception", "conversation"}
    for spec in tools.TOOL_REGISTRY.values():
        assert spec.agent_module in valid_modules
        assert spec.description
        assert spec.params_schema


@pytest.mark.asyncio
async def test_dispatch_known_tool_returns_placeholder(caplog):
    """已知工具 → 占位 handler 返回 not_implemented,并输出结构化日志。"""
    import logging

    with caplog.at_level(logging.INFO, logger="app.agents.conversation.service.tools"):
        result = await tools.dispatch(
            "navigation.start", {"destination": "地铁站"}, {"session_id": "s1"}
        )
    assert result == {"status": "not_implemented", "tool": "navigation.start"}
    assert any("【工具调用·占位】tool=navigation.start" in r.message for r in caplog.records)
    assert any("destination" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_dispatch_unknown_tool_returns_none():
    """未知工具 → None,调用方回退纯聊天。"""
    assert await tools.dispatch("unknown.tool", {}, {}) is None


@pytest.mark.asyncio
async def test_log_only_does_not_log_transcript_raw(caplog):
    """隐私保护: 识别文本原文不出现在日志里,只记录长度。"""
    import logging

    with caplog.at_level(logging.INFO, logger="app.agents.conversation.service.tools"):
        await tools.dispatch(
            "safety.sos",
            {},
            {"transcript": "救命，我被困在公园东门了", "session_id": "s1"},
        )
    combined = "\n".join(r.message for r in caplog.records)
    assert "救命" not in combined
    assert "transcript_len" in combined

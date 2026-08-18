"""工具注册表测试: 注册表完整性、占位分发、未知工具回退。"""

import pytest

from app.agents.conversation.service import tools


def test_registry_contains_planned_tools():
    """预埋的工具都应存在,且归属 Agent 模块合法。"""
    assert {
        "navigation.start",
        "navigation.location",
        "safety.sos",
        "perception.weather",
        "perception.reminder",
    } <= set(tools.TOOL_REGISTRY)
    valid_modules = {"navigation", "safety", "perception", "conversation"}
    for spec in tools.TOOL_REGISTRY.values():
        assert spec.agent_module in valid_modules
        assert spec.description
        assert spec.params_schema


def test_location_tool_routes_to_navigation_agent():
    """「查询当前位置」工具已接真实路由(非占位)。"""
    spec = tools.TOOL_REGISTRY["navigation.location"]
    assert spec.agent_module == "navigation"
    assert spec.handler is not tools._log_only


def test_all_tools_have_real_handlers():
    """全部工具已接真实 handler(路由到对应 Agent 模块),无 _log_only 占位。"""
    for name, spec in tools.TOOL_REGISTRY.items():
        assert spec.handler is not tools._log_only, f"{name} 仍是占位 handler"


@pytest.mark.asyncio
async def test_dispatch_unknown_tool_returns_none():
    """未知工具 → None,调用方回退纯聊天。"""
    assert await tools.dispatch("unknown.tool", {}, {}) is None


@pytest.mark.asyncio
async def test_log_only_does_not_log_transcript_raw(caplog):
    """隐私保护: 占位 handler 不落识别文本原文(未来新增工具先用 _log_only)。"""
    import logging

    spec = tools.TOOL_REGISTRY["navigation.start"]
    with caplog.at_level(logging.INFO, logger="app.agents.conversation.service.tools"):
        await tools._log_only(
            {},
            {"transcript": "救命，我被困在公园东门了", "session_id": "s1"},
            spec,
        )
    combined = "\n".join(r.message for r in caplog.records)
    assert "救命" not in combined
    assert "transcript_len" in combined

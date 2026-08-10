"""Orchestrator 路由冒烟测试。"""

import pytest

from app.core.agent_protocol import AgentRequest, AgentResponse
from app.agents import get_orchestrator


@pytest.mark.asyncio
async def test_orchestrator_routes_chat_to_conversation():
    """验证 chat 意图路由到 Conversation Agent。"""
    orch = get_orchestrator()
    req = AgentRequest(
        session_id="test-session",
        user_id="test-user",
        intent="chat",
    )
    resp = await orch.route(req)
    assert isinstance(resp, AgentResponse)
    assert "对话" in resp.text or "开发中" in resp.text


@pytest.mark.asyncio
async def test_orchestrator_routes_navigation():
    """验证 navigation 意图路由到 Navigation Agent。"""
    orch = get_orchestrator()
    req = AgentRequest(
        session_id="test-session",
        user_id="test-user",
        intent="navigation",
    )
    resp = await orch.route(req)
    assert isinstance(resp, AgentResponse)
    assert "导航" in resp.text or "开发中" in resp.text


@pytest.mark.asyncio
async def test_orchestrator_routes_sos():
    """验证 sos 意图路由到 Safety Agent。"""
    orch = get_orchestrator()
    req = AgentRequest(
        session_id="test-session",
        user_id="test-user",
        intent="sos",
    )
    resp = await orch.route(req)
    assert isinstance(resp, AgentResponse)
    assert "安全" in resp.text or "开发中" in resp.text


@pytest.mark.asyncio
async def test_orchestrator_routes_weather():
    """验证 weather 意图路由到 Perception Agent。"""
    orch = get_orchestrator()
    req = AgentRequest(
        session_id="test-session",
        user_id="test-user",
        intent="weather",
    )
    resp = await orch.route(req)
    assert isinstance(resp, AgentResponse)
    assert "生活" in resp.text or "开发中" in resp.text

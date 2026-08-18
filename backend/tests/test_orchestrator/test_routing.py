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
    assert "导航" in resp.text or "定位" in resp.text or "开发中" in resp.text


@pytest.mark.asyncio
async def test_orchestrator_routes_sos():
    """验证 sos 意图路由到 Safety Agent(已接真实求救服务)。"""
    orch = get_orchestrator()
    req = AgentRequest(
        session_id="test-session",
        user_id="test-user",
        intent="sos",
    )
    resp = await orch.route(req)
    assert isinstance(resp, AgentResponse)
    assert "120" in resp.text
    assert resp.action == "trigger_sos"


@pytest.mark.asyncio
async def test_orchestrator_routes_weather():
    """验证 weather 意图路由到 Perception Agent(已接真实服务,缺城市时追问)。"""
    orch = get_orchestrator()
    req = AgentRequest(
        session_id="test-session",
        user_id="test-user",
        intent="weather",
    )
    resp = await orch.route(req)
    assert isinstance(resp, AgentResponse)
    assert "城市" in resp.text
    assert resp.needs_followup is True


@pytest.mark.asyncio
async def test_orchestrator_routes_medicine_to_safety():
    """验证 medicine 意图路由到 Safety Agent(缺图片时追问上传)。"""
    orch = get_orchestrator()
    req = AgentRequest(
        session_id="test-session",
        user_id="test-user",
        intent="medicine",
    )
    resp = await orch.route(req)
    assert isinstance(resp, AgentResponse)
    assert "照片" in resp.text


@pytest.mark.asyncio
async def test_orchestrator_routes_location_to_navigation(monkeypatch):
    """验证 location 意图路由到 Navigation Agent 并返回位置播报(mock 定位,不触网)。"""
    from app.agents.navigation import agent as nav_agent
    from app.agents.navigation.service.amap import RegeoResult

    async def fake_get_location(client, lat=None, lng=None):
        return RegeoResult("北京市东城区测试路1号", "北京市", "北京市", "东城区", "110101"), "gps"

    monkeypatch.setattr(nav_agent, "get_current_location", fake_get_location)
    orch = get_orchestrator()
    req = AgentRequest(
        session_id="test-session",
        user_id="test-user",
        intent="location",
    )
    resp = await orch.route(req)
    assert isinstance(resp, AgentResponse)
    assert "测试路1号" in resp.text


@pytest.mark.asyncio
async def test_orchestrator_routes_currency_to_safety():
    """验证 currency 意图路由到 Safety Agent。"""
    orch = get_orchestrator()
    req = AgentRequest(
        session_id="test-session",
        user_id="test-user",
        intent="currency",
    )
    resp = await orch.route(req)
    assert isinstance(resp, AgentResponse)
    assert "照片" in resp.text

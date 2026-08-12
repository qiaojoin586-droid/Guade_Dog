"""Navigation Agent 契约 + 逻辑测试。"""

import pytest

from app.core.agent_protocol import AgentRequest, AgentResponse
from app.agents.navigation.agent import NavigationAgent


@pytest.mark.asyncio
async def test_handle_with_destination():
    """有目的地 → 返回路线规划播报。"""
    agent = NavigationAgent()
    req = AgentRequest(
        session_id="t1",
        user_id="u1",
        intent="navigation",
        params={"destination": "天安门"},
        context={"coords": {"lat": 39.91512, "lng": 116.397998}},
    )
    resp = await agent.handle(req)
    assert isinstance(resp, AgentResponse)
    assert resp.text
    assert resp.action == "navigate"
    assert resp.data
    assert "summary" in resp.data
    assert "steps" in resp.data


@pytest.mark.asyncio
async def test_handle_destination_not_found():
    """目的地不存在 → 返回错误提示。"""
    agent = NavigationAgent()
    req = AgentRequest(
        session_id="t1",
        user_id="u1",
        intent="navigation",
        params={"destination": "xyz不存在的奇怪地名xyz"},
        context={"coords": {"lat": 39.90923, "lng": 116.397428}},
    )
    resp = await agent.handle(req)
    assert isinstance(resp, AgentResponse)
    assert resp.text  # 必须有错误播报
    assert "找不到" in resp.text or "换个说法" in resp.text or "未找到" in resp.text


@pytest.mark.asyncio
async def test_handle_missing_destination():
    """无目的地但有坐标 → 返回当前位置。"""
    agent = NavigationAgent()
    req = AgentRequest(
        session_id="t1",
        user_id="u1",
        intent="navigation",
        params={},
        context={"coords": {"lat": 39.90923, "lng": 116.397428}},
    )
    resp = await agent.handle(req)
    assert isinstance(resp, AgentResponse)
    assert "当前" in resp.text or "您" in resp.text


@pytest.mark.asyncio
async def test_handle_returns_valid_agent_response():
    """契约冒烟：任何输入都返回合法的 AgentResponse。"""
    agent = NavigationAgent()
    req = AgentRequest(
        session_id="t1",
        user_id="u1",
        intent="navigation",
        params={},
        context={},
    )
    resp = await agent.handle(req)
    assert isinstance(resp, AgentResponse)
    assert isinstance(resp.text, str)

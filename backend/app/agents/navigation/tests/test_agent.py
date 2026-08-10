"""Navigation Agent 契约测试。"""

import pytest

from app.core.agent_protocol import AgentRequest, AgentResponse
from app.agents.navigation.agent import NavigationAgent


@pytest.mark.asyncio
async def test_navigation_handle_returns_valid_response():
    """验证 handle() 返回合法 AgentResponse。"""
    agent = NavigationAgent()
    req = AgentRequest(
        session_id="test-session",
        user_id="test-user",
        intent="navigation",
        params={"destination": "地铁站"},
        context={},
    )
    resp = await agent.handle(req)
    assert isinstance(resp, AgentResponse)
    assert resp.text  # 非空
    assert resp.needs_followup is False

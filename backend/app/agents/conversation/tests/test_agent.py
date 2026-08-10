"""Conversation Agent 契约测试。"""

import pytest

from app.core.agent_protocol import AgentRequest, AgentResponse
from app.agents.conversation.agent import ConversationAgent


@pytest.mark.asyncio
async def test_conversation_handle_returns_valid_response():
    """验证 handle() 返回合法 AgentResponse。"""
    agent = ConversationAgent()
    req = AgentRequest(
        session_id="test-session",
        user_id="test-user",
        intent="chat",
        params={},
        context={},
    )
    resp = await agent.handle(req)
    assert isinstance(resp, AgentResponse)
    assert resp.text  # 非空
    assert resp.needs_followup is False

"""契约冒烟测试。

构造任意 AgentRequest，验证 4 个模块的 handle() 都能返回合法 AgentResponse。
"""

import pytest

from app.core.agent_protocol import AgentRequest, AgentResponse
from app.agents.conversation.agent import ConversationAgent
from app.agents.navigation.agent import NavigationAgent
from app.agents.safety.agent import SafetyAgent
from app.agents.perception.agent import PerceptionAgent


@pytest.mark.asyncio
async def test_all_agents_return_valid_response():
    """4 个模块的 handle() 均返回合法 AgentResponse。"""
    req = AgentRequest(
        session_id="contract-test-session",
        user_id="contract-test-user",
        intent="chat",
        params={"test": True},
        context={"source": "contract_test"},
    )

    agents = [
        ConversationAgent(),
        NavigationAgent(),
        SafetyAgent(),
        PerceptionAgent(),
    ]

    for agent in agents:
        resp = await agent.handle(req)
        assert isinstance(resp, AgentResponse), f"{agent.__class__.__name__} 未返回 AgentResponse"
        assert isinstance(resp.text, str) and resp.text, f"{agent.__class__.__name__} 的 text 为空"
        assert resp.needs_followup is False or resp.needs_followup is True

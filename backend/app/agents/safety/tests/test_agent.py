"""Safety Agent 契约测试。"""

import pytest

from app.core.agent_protocol import AgentRequest, AgentResponse
from app.agents.safety.agent import SafetyAgent


@pytest.mark.asyncio
async def test_safety_handle_returns_valid_response():
    """验证 handle() 返回合法 AgentResponse。"""
    agent = SafetyAgent()
    req = AgentRequest(
        session_id="test-session",
        user_id="test-user",
        intent="sos",
        params={},
        context={},
    )
    resp = await agent.handle(req)
    assert isinstance(resp, AgentResponse)
    assert resp.text  # 非空
    assert resp.needs_followup is False


@pytest.mark.asyncio
async def test_handle_invalid_base64_returns_upload_hint():
    """图片 base64 无效 → 提示上传照片，而不是文不对题的文案。"""
    agent = SafetyAgent()
    req = AgentRequest(
        session_id="test-session",
        user_id="test-user",
        intent="medicine",
        params={"image_base64": "a"},
        context={},
    )
    resp = await agent.handle(req)
    assert isinstance(resp, AgentResponse)
    assert resp.text == "请上传要识别的照片"

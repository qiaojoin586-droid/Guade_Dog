"""Perception Agent 契约测试。"""

import pytest

from app.agents.perception.agent import PerceptionAgent
from app.agents.perception.service import weather
from app.core.agent_protocol import AgentRequest, AgentResponse


@pytest.mark.asyncio
async def test_perception_handle_weather_success(monkeypatch):
    """weather 意图返回天气播报文案（mock 服务，不触网）。"""

    async def fake_now(city):
        return {
            "city": city,
            "temperature": 28,
            "condition": "晴",
            "humidity": 55,
            "uv_index": 4,
            "dressing_advice": "天气炎热，建议穿短袖",
            "tts_text": f"{city}现在晴，气温28度。",
        }

    monkeypatch.setattr(weather, "get_now_weather", fake_now)
    agent = PerceptionAgent()
    req = AgentRequest(
        session_id="test-session",
        user_id="test-user",
        intent="weather",
        params={"city": "北京"},
        context={},
    )
    resp = await agent.handle(req)
    assert isinstance(resp, AgentResponse)
    assert "28度" in resp.text
    assert resp.needs_followup is False


@pytest.mark.asyncio
async def test_perception_handle_weather_missing_city():
    """缺城市 → 追问（不触网、不瞎猜城市）。"""
    agent = PerceptionAgent()
    req = AgentRequest(
        session_id="test-session",
        user_id="test-user",
        intent="weather",
        params={},
        context={},
    )
    resp = await agent.handle(req)
    assert isinstance(resp, AgentResponse)
    assert "城市" in resp.text
    assert resp.needs_followup is True


@pytest.mark.asyncio
async def test_perception_handle_other_intent_fallback():
    """未实现意图 → 占位文案。"""
    agent = PerceptionAgent()
    req = AgentRequest(
        session_id="test-session",
        user_id="test-user",
        intent="ocr",
        params={},
        context={},
    )
    resp = await agent.handle(req)
    assert isinstance(resp, AgentResponse)
    assert resp.text  # 非空

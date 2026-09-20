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
async def test_perception_handle_weather_missing_city(monkeypatch):
    """缺城市且无坐标 → 直接追问,不调定位(刻意不用 IP 猜城市)。"""
    from app.agents.perception import agent as p_agent

    called = {}

    async def fail_location(client, lat=None, lng=None):
        called["hit"] = True
        raise AssertionError("无坐标时不应调用定位服务")

    monkeypatch.setattr(p_agent, "get_current_location", fail_location)
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
    assert "hit" not in called  # 定位服务未被调用


@pytest.mark.asyncio
async def test_perception_handle_weather_auto_locate(monkeypatch):
    """未指定城市 + 前端 GPS 坐标 → 自动定位后查询当地天气。"""
    from app.agents.navigation.service.amap import RegeoResult
    from app.agents.perception import agent as p_agent

    calls: dict = {}

    async def fake_location(client, lat=None, lng=None):
        return RegeoResult("北京市东城区", "北京市", "北京市", "东城区", "110101"), "gps"

    async def fake_weather(city):
        calls["city"] = city
        return {
            "city": city,
            "temperature": 24,
            "condition": "雾",
            "humidity": 94,
            "uv_index": 2,
            "dressing_advice": "天气舒适",
            "tts_text": f"{city}现在雾，气温24度。",
        }

    monkeypatch.setattr(p_agent, "get_current_location", fake_location)
    monkeypatch.setattr(p_agent.weather, "get_now_weather", fake_weather)
    agent = PerceptionAgent()
    req = AgentRequest(
        session_id="test-session",
        user_id="test-user",
        intent="weather",
        params={},
        context={"coords": {"lat": 39.90923, "lng": 116.397428}},
    )
    resp = await agent.handle(req)
    assert calls["city"] == "北京市"  # 用定位到的城市查天气
    assert "北京" in resp.text
    assert "根据您的当前位置" in resp.text  # 自动定位所得,如实说明依据
    assert resp.needs_followup is False


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

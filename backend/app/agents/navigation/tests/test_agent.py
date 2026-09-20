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


@pytest.mark.asyncio
async def test_handle_location_intent_with_coords(monkeypatch):
    """intent="location" + GPS 坐标 → 返回当前位置播报(mock 服务,不触网)。"""
    from app.agents.navigation.service.amap import RegeoResult

    async def fake_get_location(client, lat=None, lng=None):
        return RegeoResult("北京市东城区测试路1号", "北京市", "北京市", "东城区", "110101"), "gps"

    monkeypatch.setattr("app.agents.navigation.agent.get_current_location", fake_get_location)
    agent = NavigationAgent()
    req = AgentRequest(
        session_id="t1",
        user_id="u1",
        intent="location",
        params={},
        context={"coords": {"lat": 39.90923, "lng": 116.397428}},
    )
    resp = await agent.handle(req)
    assert isinstance(resp, AgentResponse)
    assert "测试路1号" in resp.text
    assert resp.data["coords"] == {"lat": 39.90923, "lng": 116.397428}
    assert resp.data["source"] == "gps"


@pytest.mark.asyncio
async def test_handle_location_ip_source_uses_uncertain_wording(monkeypatch):
    """IP 粗定位来源 → 播报用「可能/大致」措辞并提示开定位(不装精确)。"""
    from app.agents.navigation.service.amap import RegeoResult

    async def fake_get_location(client, lat=None, lng=None):
        return RegeoResult("河南省平顶山市", "平顶山市", "河南省", "", "410400"), "ip"

    monkeypatch.setattr("app.agents.navigation.agent.get_current_location", fake_get_location)
    agent = NavigationAgent()
    req = AgentRequest(session_id="t1", user_id="u1", intent="location", params={}, context={})
    resp = await agent.handle(req)
    assert "可能" in resp.text
    assert "粗略" in resp.text
    assert "定位权限" in resp.text
    assert resp.data["source"] == "ip"
    assert "coords" not in resp.data  # IP 来源无坐标,不伪造


@pytest.mark.asyncio
async def test_handle_location_low_accuracy_wording(monkeypatch):
    """浏览器精度差(>1km,多为网络推算)→ 用「大致…附近」措辞。"""
    from app.agents.navigation.service.amap import RegeoResult

    async def fake_get_location(client, lat=None, lng=None):
        return RegeoResult("河南省平顶山市", "平顶山市", "河南省", "", "410400"), "gps"

    monkeypatch.setattr("app.agents.navigation.agent.get_current_location", fake_get_location)
    agent = NavigationAgent()
    req = AgentRequest(
        session_id="t1",
        user_id="u1",
        intent="location",
        params={},
        context={"coords": {"lat": 34.05, "lng": 113.3, "accuracy": 150000}},
    )
    resp = await agent.handle(req)
    assert "大致" in resp.text
    assert "附近" in resp.text
    assert resp.data["accuracy"] == 150000

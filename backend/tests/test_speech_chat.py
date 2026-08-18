"""chat 编排层测试: LLM 输出解析、工具分发、兜底(monkeypatch 掉 llm.complete)。"""

import json

import pytest

from app.agents.conversation.service import chat
from app.core import llm


@pytest.mark.asyncio
async def test_chat_dispatch_tool(monkeypatch):
    """LLM 选中工具 → 分发执行真实 handler(不触网),返回 chat_reply + 工具结果。"""

    async def fake_complete(prompt, model=None, json_mode=False, system=None):
        return json.dumps(
            {
                "tool": "safety.sos",
                "params": {},
                "chat_reply": "已为您触发紧急求救",
            }
        )

    monkeypatch.setattr(llm, "complete", fake_complete)
    resp = await chat.chat("救命", "s1", "u1")
    # chat_reply 与 SafetyAgent 返回的急救指引拼接播报
    assert "已为您触发紧急求救" in resp.text
    assert "120" in resp.text
    assert resp.data["tool_called"] == "safety.sos"


@pytest.mark.asyncio
async def test_chat_pure_chat(monkeypatch):
    """LLM 未选工具 → 纯聊天回复,data 为 None。"""

    async def fake_complete(prompt, model=None, json_mode=False, system=None):
        return json.dumps({"tool": None, "params": {}, "chat_reply": "你好呀,今天想去哪里?"})

    monkeypatch.setattr(llm, "complete", fake_complete)
    resp = await chat.chat("你好", "s1", "u1")
    assert resp.text == "你好呀,今天想去哪里?"
    assert resp.data is None


@pytest.mark.asyncio
async def test_chat_unknown_tool_falls_back(monkeypatch):
    """LLM 选中不存在的工具 → 回退纯聊天,不报错。"""

    async def fake_complete(prompt, model=None, json_mode=False, system=None):
        return json.dumps(
            {"tool": "nonexistent.tool", "params": {}, "chat_reply": "好的"}
        )

    monkeypatch.setattr(llm, "complete", fake_complete)
    resp = await chat.chat("随便说说", "s1", "u1")
    assert resp.text == "好的"
    assert resp.data is None


@pytest.mark.asyncio
async def test_chat_fallback_on_llm_failure(monkeypatch):
    """LLM 连续失败 → 兜底回复,系统不崩。"""

    async def fake_complete(prompt, model=None, json_mode=False, system=None):
        raise llm.LLMError("network down")

    monkeypatch.setattr(llm, "complete", fake_complete)
    resp = await chat.chat("导航到地铁站", "s1", "u1")
    assert "抱歉" in resp.text
    assert resp.data is None


@pytest.mark.asyncio
async def test_chat_fallback_on_bad_json(monkeypatch):
    """LLM 输出非 JSON → 兜底回复。"""

    async def fake_complete(prompt, model=None, json_mode=False, system=None):
        return "我不是JSON,我是纯文本"

    monkeypatch.setattr(llm, "complete", fake_complete)
    resp = await chat.chat("测试", "s1", "u1")
    assert "抱歉" in resp.text


@pytest.mark.asyncio
async def test_chat_short_ack_uses_tool_result(monkeypatch):
    """chat_reply 只是纯衔接语(≤6字)时,直接用工具结果播报,避免重复。"""

    async def fake_complete(prompt, model=None, json_mode=False, system=None):
        return json.dumps({"tool": "safety.sos", "params": {}, "chat_reply": "好的"})

    async def fake_dispatch(tool, params, context):
        return {"text": "已收到您的求救信号，请保持冷静。"}

    monkeypatch.setattr(llm, "complete", fake_complete)
    monkeypatch.setattr(chat, "dispatch", fake_dispatch)
    resp = await chat.chat("救命", "s1", "u1")
    assert resp.text == "已收到您的求救信号，请保持冷静。"


@pytest.mark.asyncio
async def test_chat_passes_coords_into_tool_context(monkeypatch):
    """前端 GPS 坐标透传进工具上下文,并拼接工具返回的位置文本。"""
    captured: dict = {}

    async def fake_dispatch(tool, params, context):
        captured.update(context)
        return {"text": "您当前在北京市东城区测试路1号", "data": {"address": "测试路1号"}}

    async def fake_complete(prompt, model=None, json_mode=False, system=None):
        return json.dumps(
            {"tool": "navigation.location", "params": {}, "chat_reply": "正在为您查询当前位置"}
        )

    monkeypatch.setattr(llm, "complete", fake_complete)
    monkeypatch.setattr(chat, "dispatch", fake_dispatch)
    resp = await chat.chat("我在哪", "s1", "u1", coords={"lat": 39.9, "lng": 116.4})

    assert captured["coords"] == {"lat": 39.9, "lng": 116.4}
    assert "正在为您查询当前位置" in resp.text
    assert "测试路1号" in resp.text
    assert resp.data["tool_called"] == "navigation.location"
    assert resp.data["tool_data"]["address"] == "测试路1号"

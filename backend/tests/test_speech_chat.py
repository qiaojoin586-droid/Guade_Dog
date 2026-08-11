"""chat 编排层测试: LLM 输出解析、工具分发、兜底(monkeypatch 掉 llm.complete)。"""

import json

import pytest

from app.agents.conversation.service import chat
from app.core import llm


@pytest.mark.asyncio
async def test_chat_dispatch_tool(monkeypatch):
    """LLM 选中工具 → 分发执行,返回 chat_reply 与 tool_called。"""

    async def fake_complete(prompt, model=None, json_mode=False, system=None):
        return json.dumps(
            {
                "tool": "navigation.start",
                "params": {"destination": "地铁站"},
                "chat_reply": "好的,正在为您规划去地铁站的路线",
            }
        )

    monkeypatch.setattr(llm, "complete", fake_complete)
    resp = await chat.chat("导航到地铁站", "s1", "u1")
    assert resp.text == "好的,正在为您规划去地铁站的路线"
    assert resp.data == {"tool_called": "navigation.start"}


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

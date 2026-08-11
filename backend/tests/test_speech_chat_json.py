"""chat 容错 JSON 解析测试(兼容星火输出的 markdown 围栏/杂文本)。"""

import pytest

from app.agents.conversation.service.chat import _extract_json


def test_parse_pure_json():
    assert _extract_json('{"tool": null, "chat_reply": "你好"}') == {
        "tool": None,
        "chat_reply": "你好",
    }


def test_parse_json_with_markdown_fence():
    raw = '```json\n{"tool": "navigation.start", "params": {"destination": "地铁站"}}\n```'
    assert _extract_json(raw)["tool"] == "navigation.start"


def test_parse_json_with_leading_text():
    raw = '好的,这是结果:\n{"tool": null, "chat_reply": "好的"}\n希望有帮助'
    assert _extract_json(raw)["chat_reply"] == "好的"


def test_parse_invalid_json_raises():
    with pytest.raises(ValueError):
        _extract_json("完全不是 JSON")

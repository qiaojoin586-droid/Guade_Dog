"""TTS 文本截断测试：UTF-8 多字节字符不切坏。"""

from app.agents.conversation.service.tts import _truncate_utf8


def test_truncate_utf8_within_limit_untouched():
    assert _truncate_utf8("你好", 10) == "你好".encode("utf-8")


def test_truncate_utf8_cuts_at_char_boundary():
    """"你好世界" 12 字节,限 10 字节 → 残缺字节被丢弃,结果仍是合法 UTF-8。"""
    out = _truncate_utf8("你好世界", 10)
    assert out.decode("utf-8") == "你好世"
    assert len(out) <= 10


def test_truncate_utf8_mixed_ascii_cjk():
    """"abc你好def" 12 字节,限 7 字节切在"好"中间 → 丢弃残缺字节。"""
    out = _truncate_utf8("abc你好def", 7)
    out.decode("utf-8")  # 不抛 UnicodeDecodeError 即为合法
    assert out.decode("utf-8") == "abc你"
    assert len(out) <= 7

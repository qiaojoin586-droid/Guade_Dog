"""手机号登录验证码（开发阶段：只打印到控制台，不发送真实短信）。

设计约定：
- 6 位数字，5 分钟有效，最多校验 5 次；
- 同一手机号 60 秒内不能重复获取（防刷）；
- 进程内内存存储，重启后失效（Phase 2 换成 Redis + 短信网关）。

上线前必须替换的点：`issue_code` 里的 `_print_code` 改为调用短信服务，
并从接口返回值中移除任何调试信息。
"""

from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

CODE_LENGTH = 6
CODE_TTL_SECONDS = 300
RESEND_INTERVAL_SECONDS = 60
MAX_ATTEMPTS = 5


@dataclass
class _CodeEntry:
    """某个手机号当前有效的验证码。"""

    code: str
    expires_at: float
    sent_at: float
    attempts: int = 0


# phone -> 验证码条目
_store: dict[str, _CodeEntry] = {}


def _print_code(phone: str, code: str) -> None:
    """把验证码打印到后端控制台（开发阶段的“短信”）。"""
    expires_min = CODE_TTL_SECONDS // 60
    print(
        "\n"
        "============================================================\n"
        f"【模拟短信验证码】手机号 {phone} 的登录验证码：{code}\n"
        f"（{expires_min} 分钟内有效，仅打印在控制台，未发送真实短信）\n"
        "============================================================\n",
        flush=True,
    )
    logger.info("模拟短信验证码已生成 phone=%s expires_in=%ss", phone, CODE_TTL_SECONDS)


def _cleanup(now: float) -> None:
    """清理已过期的验证码，避免内存无限增长。"""
    for phone in [p for p, e in _store.items() if e.expires_at < now]:
        _store.pop(phone, None)


def issue_code(phone: str) -> tuple[int, int]:
    """生成并打印验证码。

    Returns:
        (有效期秒数, 剩余可重发等待秒数)

    Raises:
        ValueError: 60 秒内重复获取、手机号格式非法
    """
    now = time.time()
    _cleanup(now)

    entry = _store.get(phone)
    if entry and now - entry.sent_at < RESEND_INTERVAL_SECONDS:
        wait = int(RESEND_INTERVAL_SECONDS - (now - entry.sent_at)) + 1
        raise ValueError(f"获取过于频繁，请 {wait} 秒后再试")

    code = "".join(str(secrets.randbelow(10)) for _ in range(CODE_LENGTH))
    _store[phone] = _CodeEntry(
        code=code,
        expires_at=now + CODE_TTL_SECONDS,
        sent_at=now,
    )
    _print_code(phone, code)
    return CODE_TTL_SECONDS, RESEND_INTERVAL_SECONDS


def verify_code(phone: str, code: str) -> None:
    """校验验证码，失败抛 ValueError（文案可直接播报）。"""
    now = time.time()
    entry = _store.get(phone)

    if entry is None:
        raise ValueError("请先获取验证码")
    if entry.expires_at < now:
        _store.pop(phone, None)
        raise ValueError("验证码已过期，请重新获取")
    if entry.attempts >= MAX_ATTEMPTS:
        _store.pop(phone, None)
        raise ValueError("验证码错误次数过多，请重新获取")

    if not secrets.compare_digest(entry.code, code):
        entry.attempts += 1
        raise ValueError("验证码不正确，请重新输入")

    # 验证通过即失效，避免重复使用
    _store.pop(phone, None)


def reset_store() -> None:
    """清空所有验证码（测试用）。"""
    _store.clear()


def peek_code(phone: str) -> str | None:
    """查看当前验证码（仅测试用，业务代码禁止调用）。"""
    entry = _store.get(phone)
    return entry.code if entry else None

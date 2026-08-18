"""语音提醒服务(进程内实现)。

职责:
  * parse_reminder_time —— 中文时间文本 → 触发时刻(支持"半小时后"/"明天上午9点"/"15:30")
  * set_reminder —— 注册提醒,到期后记录日志并尝试经 WebSocket 管理器推送

局限(如实声明):
  * 提醒保存在进程内,服务重启即丢失;
  * 到期回调已挂 WebSocket 广播钩子,但前端通道尚未接入(Phase 2),
    当前到期行为是日志 + 推送尝试。

TODO(Phase 2): 迁移到 Celery 持久化任务,前端接入 WebSocket 后提醒可真实播报。
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta

from app.core.websocket import manager

logger = logging.getLogger(__name__)

# user_id -> 到期回调任务列表(持引用防止任务被 GC)
_pending: dict[str, list[asyncio.Task]] = {}

# "5分钟后" / "2小时后"
_RELATIVE_RE = re.compile(r"(\d+)\s*(分钟|小时)后")
# "[上午|下午|晚上|中午]H点[MM分]" / "H:MM" / "H时"
_CLOCK_RE = re.compile(r"(上午|下午|晚上|中午)?\s*(\d{1,2})\s*[点:时]\s*(\d{1,2})?\s*分?")

# 常见中文数字(支持"一小时后"、"下午三点"这类口语)
_CN_DIGITS = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _normalize_time_text(text: str) -> str:
    """口语时间归一化: 半小时→30分钟、中文数字→阿拉伯数字,便于统一正则解析。"""
    # "一个半小时" 必须先于 "半小时" 处理
    text = re.sub(r"一个半\s*个?\s*小时", "90分钟", text)
    text = re.sub(r"半\s*个?\s*小时", "30分钟", text)
    # 中文数字 + 分钟/小时/点
    text = re.sub(
        r"([一二两三四五六七八九十])\s*(?=分钟|小时|点|时|:)",
        lambda m: str(_CN_DIGITS[m.group(1)]),
        text,
    )
    return text


def parse_reminder_time(text: str, now: datetime | None = None) -> datetime | None:
    """解析中文提醒时间，返回触发时刻；解析不出返回 None。

    支持：
      - 相对时间: "5分钟后"、"半小时后"、"一小时后"
      - 时刻: "上午9点"、"下午3点30分"、"下午三点"、"15:30"
      - 日期前缀: "今天/明天/后天"(无前缀时若时刻已过则顺延到明天)
    """
    text = _normalize_time_text(text or "").strip()
    if not text:
        return None
    now = now or datetime.now()

    # 1) 相对时间
    m = _RELATIVE_RE.search(text)
    if m:
        n = int(m.group(1))
        return now + (timedelta(minutes=n) if m.group(2) == "分钟" else timedelta(hours=n))

    # 2) 时刻 + 可选日期前缀
    day_delta = 0
    if "后天" in text:
        day_delta = 2
    elif "明天" in text:
        day_delta = 1

    m = _CLOCK_RE.search(text)
    if not m:
        return None

    period, hour, minute_text = m.group(1), int(m.group(2)), m.group(3)
    minute = int(minute_text or 0)
    if period == "下午" and hour < 12:
        hour += 12
    elif period == "晚上" and hour < 12:
        hour += 12
    elif period == "上午" and hour == 12:
        hour = 0
    if not (0 <= hour <= 23) or not (0 <= minute <= 59):
        return None

    due = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=day_delta)
    if due <= now:  # 时刻已过(且未写"明天/后天")→ 顺延到明天
        due += timedelta(days=1)
    return due


def format_due(due: datetime, now: datetime | None = None) -> str:
    """触发时刻的口语化描述，如「今天下午3点30分」「明天上午9点」。"""
    now = now or datetime.now()
    today = now.date()
    if due.date() == today:
        day = "今天"
    elif due.date() == today + timedelta(days=1):
        day = "明天"
    elif due.date() == today + timedelta(days=2):
        day = "后天"
    else:
        day = due.strftime("%m月%d日")

    hour, minute = due.hour, due.minute
    if hour == 0:
        clock = "凌晨0点"
    elif hour < 6:
        clock = f"凌晨{hour}点"
    elif hour < 12:
        clock = f"上午{hour}点"
    elif hour == 12:
        clock = "中午12点"
    elif hour < 18:
        clock = f"下午{hour - 12}点"
    else:
        clock = f"晚上{hour - 12}点"
    if minute:
        clock += f"{minute:02d}分"
    return day + clock


def set_reminder(user_id: str, content: str, due: datetime) -> None:
    """注册提醒；到期后记录日志并尝试推送(前端通道接入后生效)。"""
    task = asyncio.create_task(_fire(user_id, content, due))
    _pending.setdefault(user_id or "anonymous", []).append(task)


async def _fire(user_id: str, content: str, due: datetime) -> None:
    """到期回调。"""
    delay = (due - datetime.now()).total_seconds()
    try:
        if delay > 0:
            await asyncio.sleep(delay)
    except asyncio.CancelledError:
        return  # 服务关闭/测试清理,静默退出

    logger.warning("提醒到期 user_id=%s content=%s due=%s", user_id, content, due.isoformat())
    # TODO(Phase 2): 前端接入 WebSocket 后,这里按 session 推送到指定用户播报
    try:
        await manager.broadcast(
            json.dumps({"type": "reminder", "content": content, "due": due.isoformat()}, ensure_ascii=False)
        )
    except Exception:
        logger.exception("提醒推送失败(WebSocket 通道未接入) user_id=%s", user_id)


async def cancel_all() -> None:
    """取消全部未到期提醒并等待任务收尾(服务关闭/测试清理用)。"""
    tasks = [task for group in _pending.values() for task in group]
    _pending.clear()
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

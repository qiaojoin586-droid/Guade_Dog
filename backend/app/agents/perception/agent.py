"""Perception Agent 实现。

实现 Agent 契约: handle(req: AgentRequest) -> AgentResponse
本期能力: 天气查询(weather) / 语音提醒(reminder)
"""

from __future__ import annotations

import logging

from app.core.agent_protocol import AgentRequest, AgentResponse
from app.core.errors import ERR_EXT_UNAVAILABLE

from .service import reminder, weather
from .service.weather import QWeatherError

logger = logging.getLogger(__name__)

# 兜底文案（宁可说开发中，不说错）
_FALLBACK = "生活服务功能开发中，请稍后再试"


class PerceptionAgent:
    """感知 Agent —— 生活服务与政策咨询。"""

    async def handle(self, req: AgentRequest) -> AgentResponse:
        """按意图分发已实现的能力。"""
        if req.intent == "weather":
            return await self._weather(req.params or {})
        if req.intent == "reminder":
            return await self._reminder(req.params or {}, req.user_id)

        return AgentResponse(
            text=_FALLBACK,
            action=None,
            data=None,
            needs_followup=False,
        )

    async def _weather(self, params: dict) -> AgentResponse:
        """天气查询。city 缺省时追问（和风无 IP 自动定位，不瞎猜城市）。"""
        city = (params.get("city") or "").strip()
        try:
            result = await weather.get_now_weather(city)
        except ValueError as exc:
            # 城市为空 → 追问；不在内置城市表 → 播报提示并追问
            return AgentResponse(
                text=str(exc) if city else "请告诉我您要查询的城市",
                action=None,
                data=None,
                needs_followup=True,
            )
        except QWeatherError as exc:
            logger.warning("天气服务不可用: %s", exc)
            return AgentResponse(
                text="天气服务暂不可用，请稍后再试",
                action=None,
                data={"code": ERR_EXT_UNAVAILABLE},
                needs_followup=False,
            )
        return AgentResponse(
            text=result["tts_text"],
            action=None,
            data=result,
            needs_followup=False,
        )

    async def _reminder(self, params: dict, user_id: str) -> AgentResponse:
        """设置语音提醒。内容/时间缺失时追问,不瞎猜。"""
        content = (params.get("content") or "").strip()
        time_text = (params.get("time") or "").strip()

        if not content:
            return AgentResponse(
                text="请告诉我要提醒的内容",
                action=None,
                data=None,
                needs_followup=True,
            )
        due = reminder.parse_reminder_time(time_text)
        if due is None:
            return AgentResponse(
                text="请告诉我提醒时间，例如「半小时后」或「明天上午9点」",
                action=None,
                data=None,
                needs_followup=True,
            )

        reminder.set_reminder(user_id, content, due)
        return AgentResponse(
            text=f"好的，已为您设置提醒：{content}，{reminder.format_due(due)}提醒您。",
            action=None,
            data={"content": content, "time_text": time_text, "due": due.isoformat()},
            needs_followup=False,
        )

"""Perception Agent 实现。

实现 Agent 契约: handle(req: AgentRequest) -> AgentResponse
本期能力: 天气查询(weather,未指定城市时自动定位) / 语音提醒(reminder)
"""

from __future__ import annotations

import logging

from app.agents.navigation.service.amap import AmapClient, AmapError
from app.agents.navigation.service.navigation import get_current_location
from app.config import get_settings
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
            return await self._weather(req.params or {}, req.context or {})
        if req.intent == "reminder":
            return await self._reminder(req.params or {}, req.user_id)

        return AgentResponse(
            text=_FALLBACK,
            action=None,
            data=None,
            needs_followup=False,
        )

    async def _weather(self, params: dict, context: dict) -> AgentResponse:
        """天气查询。

        用户未指定城市时,用前端 GPS 坐标自动定位当地城市查天气;
        没有坐标或定位失败 → 追问城市。
        刻意不用 IP 粗定位:IP 只有城市级精度且常跨市错误,报错城市
        比让用户再问一次更糟(宁可说不确定,不可说错)。
        """
        city = (params.get("city") or "").strip()
        located = False  # 是否走了自动定位
        if not city:
            coords = context.get("coords") or {}
            lat, lng = coords.get("lat"), coords.get("lng")
            # 设计约定：没有前端 GPS 坐标时直接追问城市，不用 IP 猜城市
            if lat is not None and lng is not None:
                try:
                    client = AmapClient(key=get_settings().AMAP_API_KEY or "")
                    regeo, _ = await get_current_location(client, lat=lat, lng=lng)
                    city = (regeo.city or regeo.province or "").strip()
                    located = True
                except AmapError as exc:
                    logger.warning("天气自动定位失败,回退追问: %s", exc)

        try:
            result = await weather.get_now_weather(city)
        except ValueError as exc:
            # 城市为空(无坐标/定位失败) → 追问;城市解析不到 → 播报提示并追问
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
        if located:
            # 自动定位所得的城市可能与用户实际位置有偏差,播报如实说明依据
            result["tts_text"] = f"根据您的当前位置，{result['tts_text']}"
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

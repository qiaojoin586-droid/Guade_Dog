"""Navigation Agent 实现。

实现 Agent 契约: handle(req: AgentRequest) -> AgentResponse
负责: 当前位置查询 + 步行路线规划 + 播报文案生成。
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.core.agent_protocol import AgentRequest, AgentResponse

from .service.amap import AmapClient, AmapError
from .service.navigation import get_current_location, plan_route

logger = logging.getLogger(__name__)


class NavigationAgent:
    """导航 Agent —— 路径规划。"""

    def __init__(self) -> None:
        self._client: AmapClient | None = None

    def _get_client(self) -> AmapClient:
        """懒初始化高德客户端（读取配置中的 key）。"""
        if self._client is None:
            key = get_settings().AMAP_API_KEY or ""
            if not key:
                logger.warning("AMAP_API_KEY 未配置，高德 API 不可用")
            self._client = AmapClient(key=key)
        return self._client

    async def handle(self, req: AgentRequest) -> AgentResponse:
        """处理导航请求。

        intent="navigation" 时：
          - params["destination"] 必填 → 规划路线
          - 无 destination 但有 coords → 查询当前位置
          - context["coords"] 可携带前端坐标 {"lat": 39.9, "lng": 116.4}
        """
        params = req.params or {}
        context = req.context or {}
        destination = params.get("destination", "").strip()

        try:
            if destination:
                # ── 路线规划 ──
                coords = context.get("coords") or {}
                origin_lat = coords.get("lat")
                origin_lng = coords.get("lng")

                data = await plan_route(
                    self._get_client(),
                    destination=destination,
                    origin_lat=origin_lat,
                    origin_lng=origin_lng,
                )
                return AgentResponse(
                    text=data["tts_text"],
                    action="navigate",
                    data=data,
                    needs_followup=False,
                )
            else:
                # ── 当前位置 ──
                coords = context.get("coords") or {}
                lat = coords.get("lat")
                lng = coords.get("lng")

                regeo, source = await get_current_location(
                    self._get_client(),
                    lat=lat,
                    lng=lng,
                )
                tts_text = f"您当前在{regeo.formatted_address}"
                return AgentResponse(
                    text=tts_text,
                    action=None,
                    data={
                        "coords": {"lat": lat, "lng": lng},
                        "address": regeo.formatted_address,
                        "city": regeo.city,
                        "source": source,
                        "tts_text": tts_text,
                    },
                    needs_followup=False,
                )

        except (AmapError, ValueError) as exc:
            logger.warning("导航请求处理失败: %s", exc)
            msg = str(exc)
            return AgentResponse(
                text=msg,
                action=None,
                data={"error": msg},
                needs_followup=("换个说法" in msg or "找不到" in msg or "未找到" in msg),
            )

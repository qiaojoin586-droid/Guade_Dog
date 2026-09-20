"""Navigation Agent 实现。

实现 Agent 契约: handle(req: AgentRequest) -> AgentResponse
负责: 当前位置查询 + 步行路线规划 + 播报文案生成。
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.core.agent_protocol import AgentRequest, AgentResponse

from .service.amap import AmapClient, AmapError
from .service.navigation import get_current_location, get_distance, plan_route

logger = logging.getLogger(__name__)

# 定位精度阈值(米): 浏览器自报精度超过此值,播报措辞改为不确定口吻。
# 桌面浏览器无 GPS 芯片,WiFi/网络推算的精度可能上百公里且跨市错误。
_ACCURACY_WARN_M = 1000.0


def _build_location_text(address: str, source: str, accuracy: float | None) -> str:
    """按定位来源与精度生成诚实的位置播报。

    - IP 粗定位只有城市级精度且可能跨市错误 → 明说"大致/可能"并提示开定位;
    - 浏览器坐标精度差(>1km,多为网络推算)→ 用"大致在…附近"措辞;
    - 高精度 GPS → 才用确定口吻"您当前在…"。
    """
    if source == "ip":
        return (
            f"根据网络IP粗略定位，您可能在{address}附近，误差可能较大。"
            f"请开启手机定位权限获取精确位置。"
        )
    if accuracy is not None and accuracy > _ACCURACY_WARN_M:
        return f"根据当前位置大致判断，您在{address}附近，定位精度较低，可能有偏差。"
    return f"您当前在{address}"


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
          - 无 destination → 查询当前位置
        intent="location" 时 → 查询当前位置
        intent="distance" 时 → 查询到目的地的直线距离(区别于路线规划)
        context["coords"] 可携带前端坐标 {"lat": 39.9, "lng": 116.4}
        """
        params = req.params or {}
        context = req.context or {}
        destination = params.get("destination", "").strip()

        try:
            if req.intent == "distance":
                # ── 距离查询("有多远",不做步行规划) ──
                coords = context.get("coords") or {}
                data = await get_distance(
                    self._get_client(),
                    destination=destination,
                    origin_lat=coords.get("lat"),
                    origin_lng=coords.get("lng"),
                )
                return AgentResponse(
                    text=data["tts_text"],
                    action=None,
                    data=data,
                    needs_followup=False,
                )
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
                accuracy = coords.get("accuracy")

                regeo, source = await get_current_location(
                    self._get_client(),
                    lat=lat,
                    lng=lng,
                )
                logger.info(
                    "定位查询完成 source=%s accuracy=%s address=%s",
                    source, accuracy, regeo.formatted_address,
                )
                tts_text = _build_location_text(regeo.formatted_address, source, accuracy)
                data = {
                    "address": regeo.formatted_address,
                    "city": regeo.city,
                    "source": source,
                    "accuracy": accuracy,
                    "tts_text": tts_text,
                }
                # IP 粗定位拿不到精确坐标时不返回伪坐标
                if lat is not None and lng is not None:
                    data["coords"] = {"lat": lat, "lng": lng}
                return AgentResponse(
                    text=tts_text,
                    action=None,
                    data=data,
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

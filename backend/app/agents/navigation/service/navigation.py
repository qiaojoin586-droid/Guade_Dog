"""导航业务编排。

职责:
  1. 确定起点（前端坐标 > IP 粗定位 > 失败）
  2. 调高德步行规划
  3. LLM 润色播报文案（失败则拼接原始 instruction 兜底）

本模块只依赖 amap.py（高德客户端）和 core/llm.py（LLM），不感知 HTTP 层。
"""

from __future__ import annotations

import logging
import math

from app.config import get_settings
from app.core.llm import complete, LLMError
from .amap import AmapClient, AmapError, RegeoResult, WalkingResult

logger = logging.getLogger(__name__)

# ----------------------------------------------------------
# LLM 润色 system prompt
# ----------------------------------------------------------

_NAVIGATION_PROMPT = (
    "你是视障用户的导航播报员。根据步行路线信息生成一段口语化播报文本。\n"
    "规则：\n"
    "1. 先说总览：「全程约{distance}米，大约需要{duration}分钟」\n"
    "2. 再说前{top_n}步关键转向指令，用「先…然后…接着…」串联\n"
    "3. 简洁自然，用「您」称呼用户，不要说「播报完毕」之类的结束语\n"
    "4. 只输出播报文本，不要加任何解释、标注或前缀\n"
    "\n"
    "路线信息：\n{steps_text}"
)


def _build_tts_text(result: WalkingResult, top_n: int = 3) -> str:
    """拼接高德原始 instruction 作为兜底播报文案（LLM 失败时用）。"""
    d_m = result.distance_m
    d_min = math.ceil(result.duration_s / 60)
    parts = [f"全程约{d_m}米，大约需要{d_min}分钟。"]
    for i, step in enumerate(result.steps[:top_n]):
        parts.append(f"第{i + 1}步：{step.instruction}")
    return "。".join(parts)


def _format_steps_for_llm(result: WalkingResult) -> str:
    """将全部步骤格式化为 LLM prompt 可用的文本。"""
    lines: list[str] = []
    for i, step in enumerate(result.steps):
        lines.append(f"  {i + 1}. {step.instruction}（{step.distance_m}米）")
    return "\n".join(lines)


# ----------------------------------------------------------
# 公开 API
# ----------------------------------------------------------


async def get_current_location(
    client: AmapClient,
    lat: float | None = None,
    lng: float | None = None,
) -> tuple[RegeoResult, str]:
    """获取当前位置（三级降级链）。

    Returns:
        (regeo_result, source) —— source 为 "gps" 或 "ip"。

    Raises:
        AmapError: GPS 和 IP 定位都失败。
    """
    # 第 1 级：前端 GPS 坐标 → 逆地理编码
    if lat is not None and lng is not None:
        try:
            result = await client.regeo(lat, lng)
            return result, "gps"
        except AmapError:
            logger.warning("GPS 逆地理编码失败，降级为 IP 定位")

    # 第 2 级：IP 粗定位
    result = await client.ip_location()
    if result is not None:
        return result, "ip"

    # 第 3 级：明确失败
    raise AmapError("定位失败，请检查定位权限", code="LOCATION_FAILED")


async def plan_route(
    client: AmapClient,
    destination: str,
    origin_lat: float | None = None,
    origin_lng: float | None = None,
) -> dict:
    """规划步行路线并生成播报文案。

    Args:
        client: 高德客户端实例。
        destination: 目的地地址/名称。
        origin_lat / origin_lng: 起点 GPS 坐标，不传则用 IP 粗定位兜底。

    Returns:
        dict 包含 summary / steps / tts_text，结构与 RouteOut 对齐。

    Raises:
        ValueError: destination 为空或起点无法确定。
        AmapError: 高德 API 失败。
    """
    if not destination.strip():
        raise ValueError("目的地不能为空")

    # 1. 地理编码：目的地文字 → 坐标
    try:
        geo_result = await client.geocode(destination)
    except AmapError:
        geo_result = None
    if geo_result is None:
        raise ValueError(f"没有找到「{destination}」，请换个说法")
    dest_coords: tuple[float, float] = geo_result.location

    # 2. 确定起点
    origin: tuple[float, float]
    start_address = ""

    if origin_lat is not None and origin_lng is not None:
        origin = (origin_lat, origin_lng)
        try:
            regeo = await client.regeo(origin_lat, origin_lng)
            start_address = regeo.formatted_address
        except AmapError:
            start_address = f"({origin_lat:.4f}, {origin_lng:.4f})"
    else:
        # 步行规划需要精确起点坐标，IP 粗定位精度不足以规划步行路线
        raise ValueError("未获取到精确位置，请开启 GPS 定位后重试")

    # 2. 调高德步行规划
    try:
        walking_result = await client.walking(origin, dest_coords)
    except AmapError as e:
        if "INVALID_USER_KEY" in str(e):
            raise AmapError("导航服务暂不可用，请稍后再试", code="50021")
        if "TOO_FAR" in str(e) or "OVER_DIRECTION_RANGE" in str(e):
            raise AmapError("目的地距离太远，建议乘车前往", code="40200")
        raise  # 其他错误原样抛出，由 api 层统一处理

    # 3. 生成播报文案
    tts_text = await _polish_route_text(walking_result)

    # 4. 组装返回
    d_min = math.ceil(walking_result.duration_s / 60)
    return {
        "summary": {
            "distance_m": walking_result.distance_m,
            "duration_min": d_min,
            "start_address": start_address,
            "end_address": walking_result.dest_address or destination,
        },
        "steps": [
            {
                "instruction": s.instruction,
                "distance_m": s.distance_m,
                "duration_s": s.duration_s,
            }
            for s in walking_result.steps
        ],
        "tts_text": tts_text,
    }


async def _polish_route_text(result: WalkingResult, top_n: int = 3) -> str:
    """LLM 润色播报文案；失败则返回原始拼接兜底。"""
    steps_text = _format_steps_for_llm(result)
    d_min = math.ceil(result.duration_s / 60)
    prompt = _NAVIGATION_PROMPT.format(
        distance=result.distance_m,
        duration=d_min,
        top_n=min(top_n, len(result.steps)),
        steps_text=steps_text,
    )

    try:
        settings = get_settings()
        text = await complete(
            prompt,
            model=settings.DASHSCOPE_MODEL,
            json_mode=False,
            temperature=0.3,
        )
        if text and len(text.strip()) >= 10:
            return text.strip()
        logger.warning("LLM 返回内容过短，使用兜底播报")
    except LLMError:
        logger.warning("LLM 润色失败，使用原始 instruction 兜底播报", exc_info=True)

    return _build_tts_text(result, top_n=top_n)


# ----------------------------------------------------------
# 距离查询("有多远"意图,区别于路线规划)
# ----------------------------------------------------------

_EARTH_RADIUS_M = 6371008.8


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    """两点球面直线距离(米)。"""
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlng / 2) ** 2
    )
    return int(_EARTH_RADIUS_M * 2 * math.asin(math.sqrt(a)))


def _format_distance(dist_m: int) -> str:
    """距离口语化: <1km 用米,<100km 保留 1 位小数,更远取整公里。"""
    if dist_m < 1000:
        return f"{dist_m}米"
    km = dist_m / 1000
    return f"{km:.0f}公里" if km >= 100 else f"{km:.1f}公里"


async def get_distance(
    client: AmapClient,
    destination: str,
    origin_lat: float | None,
    origin_lng: float | None,
) -> dict:
    """查询当前位置到目的地的直线距离(球面距离),返回结构化结果与播报文案。

    注意: 这是「有多远」查询,不是步行路线规划——远距离目的地(如跨省)
    也能直接回答,不会像 walking 一样报 TOO_FAR。

    Raises:
        ValueError: 目的地为空 / 起点无坐标 / 目的地解析不到 / 服务失败。
    """
    if not destination.strip():
        raise ValueError("目的地不能为空")
    if origin_lat is None or origin_lng is None:
        raise ValueError("未获取到精确位置，请开启 GPS 定位后重试")

    try:
        geo_result = await client.geocode(destination)
    except AmapError as exc:
        raise ValueError("暂时无法计算距离，请稍后再试") from exc
    if geo_result is None:
        raise ValueError(f"没有找到「{destination}」，请换个说法")

    dest_lat, dest_lng = geo_result.location
    dist_m = _haversine_m(origin_lat, origin_lng, dest_lat, dest_lng)
    dist_text = _format_distance(dist_m)

    return {
        "destination": destination,
        "distance_m": dist_m,
        "distance_text": dist_text,
        "origin": {"lat": origin_lat, "lng": origin_lng},
        "dest_coords": {"lat": dest_lat, "lng": dest_lng},
        "tts_text": f"距离{destination}约{dist_text}，这是直线距离。",
    }

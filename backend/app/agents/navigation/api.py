"""Navigation Agent 路由。

路由: /navigation/location (GET), /navigation/route (POST)
归属: 人B（Navigation 负责人）
"""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.config import get_settings
from app.core.errors import (
    ERR_EXT_UNAVAILABLE,
    ERR_INVALID_INPUT,
    ERR_NOT_FOUND,
    build_error_response,
    build_success_response,
)

from .schemas import (
    CoordsOut,
    LocationOut,
    RouteOut,
    RouteRequest,
)
from .service.amap import AmapClient, AmapError
from .service.navigation import get_current_location, plan_route

router = APIRouter(prefix="/api/v1", tags=["navigation"])


def _rid(request: Request) -> str:
    """取 request_id。"""
    return getattr(request.state, "request_id", "")


# ============================================================
# 连通性检查
# ============================================================


@router.get("/navigation/ping")
async def ping():
    return build_success_response({"module": "navigation"})


# ============================================================
# 当前位置
# ============================================================


@router.get("/navigation/location")
async def get_location(
    request: Request,
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
):
    """逆地理编码：经纬度 → 地址（三级降级链）。

    GET /api/v1/navigation/location?lat=39.90923&lng=116.397428
    GET /api/v1/navigation/location （无参数时直接用 IP 粗定位）
    """
    key = get_settings().AMAP_API_KEY or ""
    if not key:
        return build_error_response(
            ERR_EXT_UNAVAILABLE, "导航服务暂不可用", detail="AMAP_API_KEY 未配置", request_id=_rid(request),
        )

    client = AmapClient(key=key)
    # 三级降级：GPS 逆地理编码 → IP 粗定位 → 失败播报
    try:
        regeo, source = await get_current_location(client, lat=lat, lng=lng)
    except AmapError:
        return build_error_response(
            ERR_EXT_UNAVAILABLE, "无法确定您的位置，请检查定位权限",
            detail="GPS和IP定位均失败", request_id=_rid(request),
        )

    tts_text = f"您当前在{regeo.formatted_address}"
    return build_success_response(
        LocationOut(
            coords=CoordsOut(lat=lat or 0, lng=lng or 0),
            address=regeo.formatted_address,
            city=regeo.city or regeo.province,
            source=source,
            tts_text=tts_text,
        ).model_dump(),
        request_id=_rid(request),
    )


# ============================================================
# 路线规划
# ============================================================


@router.post("/navigation/route")
async def route_plan(request: Request, body: RouteRequest):
    """步行路线规划。

    POST /api/v1/navigation/route
    { "destination": "地铁站", "origin": { "lat": 39.9, "lng": 116.4 } }
    """
    key = get_settings().AMAP_API_KEY or ""
    if not key:
        return build_error_response(
            ERR_EXT_UNAVAILABLE, "导航服务暂不可用", detail="AMAP_API_KEY 未配置", request_id=_rid(request),
        )

    client = AmapClient(key=key)
    origin_lat = body.origin.lat if body.origin else None
    origin_lng = body.origin.lng if body.origin else None

    try:
        data = await plan_route(
            client, destination=body.destination,
            origin_lat=origin_lat, origin_lng=origin_lng,
        )
    except ValueError as exc:
        return build_error_response(
            ERR_INVALID_INPUT, str(exc), detail="目的地为空或位置无法确定", request_id=_rid(request),
        )
    except AmapError as exc:
        code = ERR_EXT_UNAVAILABLE
        msg = "导航服务暂不可用，请稍后再试"
        if "换个说法" in str(exc):
            code = ERR_NOT_FOUND
            msg = str(exc)
        return build_error_response(code, msg, detail=str(exc), request_id=_rid(request))

    s = data["summary"]
    route_out = RouteOut(
        summary=RouteSummaryOut(
            distance_m=s["distance_m"], duration_min=s["duration_min"],
            start_address=s["start_address"], end_address=s["end_address"],
        ),
        steps=[RouteStepOut(**step) for step in data["steps"]],
        tts_text=data["tts_text"],
    )
    return build_success_response(route_out.model_dump(), request_id=_rid(request))

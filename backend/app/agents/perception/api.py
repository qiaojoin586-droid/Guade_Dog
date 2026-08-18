"""Perception Agent 路由。

路由: /perception/weather (GET)
归属: 人D（Perception 负责人）
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request

from app.auth.models import User
from app.core.errors import (
    ERR_EXT_UNAVAILABLE,
    ERR_INVALID_INPUT,
    build_error_response,
    build_success_response,
)
from app.dependencies import get_current_user

from .schemas import WeatherOut
from .service.weather import QWeatherError, get_now_weather

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["perception"])


def _rid(request: Request) -> str:
    """取 request_id。"""
    return getattr(request.state, "request_id", "")


@router.get("/perception/ping")
async def ping():
    """Perception 模块连通性检查。"""
    return build_success_response({"module": "perception"})


@router.get("/perception/weather", summary="实时天气(和风天气)")
async def get_weather(
    request: Request,
    city: str = Query("", max_length=50, description="城市名,如 北京"),
    current_user: User = Depends(get_current_user),
):
    """查询城市实时天气,返回温度/天气现象/湿度/紫外线/穿衣建议与播报文案。

    GET /api/v1/perception/weather?city=北京
    """
    try:
        result = await get_now_weather(city)
    except ValueError as exc:
        # 城市为空 → 追问；城市不在内置表中 → 原样播报服务给出的提示
        message = "请告诉我您要查询的城市" if not city.strip() else str(exc)
        return build_error_response(
            ERR_INVALID_INPUT, message, request_id=_rid(request),
        )
    except QWeatherError as exc:
        logger.warning("天气查询失败: %s", exc)
        return build_error_response(
            ERR_EXT_UNAVAILABLE, "天气服务暂不可用，请稍后再试",
            detail=str(exc), request_id=_rid(request),
        )

    return build_success_response(
        WeatherOut(**result).model_dump(), request_id=_rid(request),
    )

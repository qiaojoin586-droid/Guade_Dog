"""Navigation Agent 路由。

路由: /navigation/*, /ws/navigation
归属: 人B（Navigation 负责人）
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.errors import build_success_response

router = APIRouter(prefix="/api/v1", tags=["navigation"])


@router.get("/navigation/ping")
async def ping():
    """Navigation 模块连通性检查。"""
    return build_success_response({"module": "navigation"})

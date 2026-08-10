"""Safety Agent 路由。

路由: /safety/*
归属: 人C（Safety 负责人）
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.errors import build_success_response

router = APIRouter(prefix="/api/v1", tags=["safety"])


@router.get("/safety/ping")
async def ping():
    """Safety 模块连通性检查。"""
    return build_success_response({"module": "safety"})

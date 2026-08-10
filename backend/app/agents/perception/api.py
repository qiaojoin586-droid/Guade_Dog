"""Perception Agent 路由。

路由: /perception/*, /reminder/*, /policy/*
归属: 人D（Perception 负责人）
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.errors import build_success_response

router = APIRouter(prefix="/api/v1", tags=["perception"])


@router.get("/perception/ping")
async def ping():
    """Perception 模块连通性检查。"""
    return build_success_response({"module": "perception"})

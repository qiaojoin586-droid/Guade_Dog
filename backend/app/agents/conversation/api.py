"""Conversation Agent 路由。

路由: /speech/*, /ws/chat, /auth/*, /family/*
归属: 人A（Conversation 负责人）
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.errors import build_success_response

router = APIRouter(prefix="/api/v1", tags=["conversation"])


@router.get("/conversation/ping")
async def ping():
    """Conversation 模块连通性检查。"""
    return build_success_response({"module": "conversation"})

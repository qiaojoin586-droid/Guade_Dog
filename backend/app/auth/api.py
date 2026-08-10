"""认证 API 路由。

提供注册、登录和 Token 刷新端点。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.auth.service import login_user, refresh_user_token, register_user
from app.core.errors import ERR_INVALID_INPUT, build_error_response, build_success_response
from app.dependencies import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _error_response(status_code: int, message: str, request_id: str = "") -> JSONResponse:
    """构造统一格式的错误响应（带正确的 HTTP 状态码）。"""
    return JSONResponse(
        status_code=status_code,
        content=build_error_response(
            code=ERR_INVALID_INPUT,
            message=message,
            request_id=request_id,
        ),
    )


@router.post("/register")
async def register(
    req: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """用户注册。"""
    request_id = request.headers.get("X-Request-ID", "")
    try:
        result: RegisterResponse = await register_user(db, req)
        return build_success_response(
            data={
                "user_id": result.user_id,
                "name": result.name,
                "role": result.role,
            },
            request_id=request_id,
        )
    except ValueError as e:
        return _error_response(400, str(e), request_id)


@router.post("/login")
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """用户登录。"""
    request_id = request.headers.get("X-Request-ID", "")
    try:
        result: LoginResponse = await login_user(db, req)
        return build_success_response(
            data={
                "access_token": result.access_token,
                "refresh_token": result.refresh_token,
                "token_type": result.token_type,
                "user_id": result.user_id,
                "name": result.name,
                "role": result.role,
                "phone": result.phone,
                "email": result.email,
                "avatar_url": result.avatar_url,
            },
            request_id=request_id,
        )
    except ValueError as e:
        return _error_response(400, str(e), request_id)


@router.post("/refresh")
async def refresh(
    req: RefreshRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """使用 refresh token 换取新的 JWT 双 Token。"""
    request_id = request.headers.get("X-Request-ID", "")
    try:
        result: RefreshResponse = await refresh_user_token(db, req)
        return build_success_response(
            data={
                "access_token": result.access_token,
                "refresh_token": result.refresh_token,
                "token_type": result.token_type,
            },
            request_id=request_id,
        )
    except ValueError as e:
        return _error_response(401, str(e), request_id)

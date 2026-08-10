"""用户资料 API 路由。

提供获取和更新当前登录用户资料的端点。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.core.errors import ERR_INVALID_INPUT, build_error_response, build_success_response
from app.dependencies import get_current_user, get_db_session
from app.users.schemas import UpdateProfileRequest
from app.users.service import get_user_profile, update_user_profile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me")
async def get_me(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """获取当前登录用户的完整信息。"""
    request_id = request.headers.get("X-Request-ID", "")
    profile = await get_user_profile(current_user)
    return build_success_response(
        data=profile.model_dump(),
        request_id=request_id,
    )


@router.put("/me")
async def update_me(
    req: UpdateProfileRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    """更新当前登录用户的资料。"""
    request_id = request.headers.get("X-Request-ID", "")
    try:
        profile = await update_user_profile(db, current_user, req)
        return build_success_response(
            data=profile.model_dump(),
            request_id=request_id,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content=build_error_response(
                code=ERR_INVALID_INPUT,
                message=str(e),
                request_id=request_id,
            ),
        )

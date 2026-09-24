"""常用地址 API 路由。

GET    /api/v1/addresses          地址列表
POST   /api/v1/addresses          新增地址
PUT    /api/v1/addresses/{id}     修改地址
DELETE /api/v1/addresses/{id}     删除地址

语音说“添加地址、公司、xxx”时，由 conversation 指令层调用本模块 service，
不经过 HTTP，保证一次语音只落一次库。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.addresses.schemas import AddressCreate, AddressOut, AddressUpdate
from app.addresses.service import (
    create_address,
    delete_address,
    list_addresses,
    update_address,
)
from app.auth.models import User
from app.core.errors import ERR_INVALID_INPUT, ERR_NOT_FOUND, build_error_response, build_success_response
from app.dependencies import get_current_user, get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/addresses", tags=["addresses"])


def _error(status_code: int, message: str, code: int, request_id: str = "") -> JSONResponse:
    """构造统一格式的错误响应。"""
    return JSONResponse(
        status_code=status_code,
        content=build_error_response(code=code, message=message, request_id=request_id),
    )


@router.get("")
async def get_addresses(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """返回当前用户的常用地址。"""
    request_id = request.headers.get("X-Request-ID", "")
    items = await list_addresses(db, current_user.id)
    return build_success_response(
        data=[AddressOut.model_validate(item).model_dump(mode="json") for item in items],
        request_id=request_id,
    )


@router.post("")
async def add_address(
    req: AddressCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """新增常用地址。"""
    request_id = request.headers.get("X-Request-ID", "")
    try:
        item = await create_address(db, current_user.id, req)
    except ValueError as exc:
        return _error(400, str(exc), ERR_INVALID_INPUT, request_id)
    return build_success_response(
        data=AddressOut.model_validate(item).model_dump(mode="json"),
        request_id=request_id,
    )


@router.put("/{address_id}")
async def edit_address(
    address_id: int,
    req: AddressUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """修改常用地址。"""
    request_id = request.headers.get("X-Request-ID", "")
    try:
        item = await update_address(db, current_user.id, address_id, req)
    except ValueError as exc:
        return _error(400, str(exc), ERR_NOT_FOUND, request_id)
    return build_success_response(
        data=AddressOut.model_validate(item).model_dump(mode="json"),
        request_id=request_id,
    )


@router.delete("/{address_id}")
async def remove_address(
    address_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """删除常用地址。"""
    request_id = request.headers.get("X-Request-ID", "")
    try:
        await delete_address(db, current_user.id, address_id)
    except ValueError as exc:
        return _error(404, str(exc), ERR_NOT_FOUND, request_id)
    return build_success_response(data={"deleted": address_id}, request_id=request_id)

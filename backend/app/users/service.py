"""用户资料业务逻辑。

提供获取和更新用户资料的服务。
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.users.schemas import UpdateProfileRequest, UserProfileResponse


def user_to_response(user: User) -> UserProfileResponse:
    """将 User 模型转换为响应 Schema。"""
    return UserProfileResponse(
        user_id=user.id,
        phone=user.phone,
        email=user.email,
        name=user.name,
        role=user.role,
        status=user.status,
        avatar_url=user.avatar_url,
        medical_notes=user.medical_notes,
        created_at=user.created_at.isoformat() if user.created_at else "",
        updated_at=user.updated_at.isoformat() if user.updated_at else "",
    )


async def get_user_profile(user: User) -> UserProfileResponse:
    """获取用户资料。"""
    return user_to_response(user)


async def update_user_profile(
    db: AsyncSession,
    user: User,
    req: UpdateProfileRequest,
) -> UserProfileResponse:
    """更新用户资料。

    仅更新请求体中非 None 的字段。
    校验手机号/邮箱的唯一性。
    """
    # 收集需要更新的字段（过滤掉 None 和空字符串）
    updates: dict[str, Optional[str]] = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.phone is not None and req.phone != "":
        updates["phone"] = req.phone
    if req.email is not None and req.email != "":
        updates["email"] = req.email
    if req.avatar_url is not None:
        updates["avatar_url"] = req.avatar_url

    if not updates:
        # 没有需要更新的字段，直接返回当前用户信息
        return user_to_response(user)

    # 校验手机号唯一性
    if "phone" in updates:
        stmt = select(User).where(User.phone == updates["phone"], User.id != user.id)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError("该手机号已被其他用户使用")

    # 校验邮箱唯一性
    if "email" in updates:
        stmt = select(User).where(User.email == updates["email"], User.id != user.id)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise ValueError("该邮箱已被其他用户使用")

    # 执行更新
    for field, value in updates.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return user_to_response(user)

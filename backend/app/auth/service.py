"""认证业务逻辑。

提供密码哈希、用户查询、注册、登录等服务。
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.schemas import LoginRequest, LoginResponse, RegisterRequest, RegisterResponse
from app.core.security import create_access_token, create_refresh_token


def hash_password(password: str) -> str:
    """使用 bcrypt 对密码进行哈希。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码是否匹配哈希值。"""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


async def find_user_by_account(db: AsyncSession, account: str) -> Optional[User]:
    """根据手机号或邮箱查找用户。"""
    # 先尝试手机号匹配
    stmt = select(User).where(User.phone == account)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user:
        return user

    # 再尝试邮箱匹配
    stmt = select(User).where(User.email == account)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def find_user_by_phone(db: AsyncSession, phone: str) -> Optional[User]:
    """根据手机号查找用户。"""
    stmt = select(User).where(User.phone == phone)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, req: RegisterRequest) -> RegisterResponse:
    """注册新用户。"""
    # 检查手机号是否已存在
    existing = await find_user_by_phone(db, req.phone)
    if existing:
        raise ValueError("该手机号已注册")

    user = User(
        phone=req.phone,
        password_hash=hash_password(req.password),
        name=req.name,
        role=req.role,
        status="active",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return RegisterResponse(user_id=user.id, name=user.name, role=user.role)


async def login_user(db: AsyncSession, req: LoginRequest) -> LoginResponse:
    """用户登录，验证密码并签发 JWT。"""
    user = await find_user_by_account(db, req.account)
    if not user:
        raise ValueError("账号或密码错误")

    if user.status != "active":
        raise ValueError("账号已被禁用")

    if not verify_password(req.password, user.password_hash):
        raise ValueError("账号或密码错误")

    token_data = {"user_id": user.id, "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        name=user.name,
        role=user.role,
        phone=user.phone,
        email=user.email,
        avatar_url=user.avatar_url,
    )

"""认证业务逻辑。

提供密码哈希、用户查询、注册、登录、Token 刷新等服务。
"""

from __future__ import annotations

import logging

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.schemas import (
    CodeLoginRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.auth.verification import verify_code
from app.config import get_settings
from app.core.security import create_access_token, create_refresh_token

logger = logging.getLogger(__name__)


def normalize_password(password: str) -> bytes:
    """bcrypt 仅支持 72 字节，超长部分截断（注册与登录使用同一规则，保持兼容）。"""
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    """使用 bcrypt 对密码进行哈希。"""
    return bcrypt.hashpw(normalize_password(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码是否匹配哈希值。"""
    return bcrypt.checkpw(normalize_password(password), password_hash.encode("utf-8"))


async def find_user_by_account(db: AsyncSession, account: str) -> User | None:
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


async def find_user_by_phone(db: AsyncSession, phone: str) -> User | None:
    """根据手机号查找用户。"""
    stmt = select(User).where(User.phone == phone)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def find_user_by_email(db: AsyncSession, email: str) -> User | None:
    """根据邮箱查找用户。"""
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, req: RegisterRequest) -> RegisterResponse:
    """注册新用户。"""
    # 检查手机号是否已存在
    if req.phone:
        existing = await find_user_by_phone(db, req.phone)
        if existing:
            raise ValueError("该手机号已注册")

    # 检查邮箱是否已存在
    if req.email:
        existing = await find_user_by_email(db, req.email)
        if existing:
            raise ValueError("该邮箱已注册")

    user = User(
        phone=req.phone,
        email=req.email,
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

    # 验证码登录创建的账号没有可用密码，禁止走密码登录
    if not is_password_login_allowed(user):
        raise ValueError("该账号请使用手机号验证码登录")

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


# 验证码登录自动创建的账号没有真实密码，用此前缀标记，密码登录直接拒绝
_CODE_LOGIN_PASSWORD_HASH = "!code-login"


def is_password_login_allowed(user: User) -> bool:
    """账号是否允许密码登录（验证码自动建号的账号不允许）。"""
    return bool(user.password_hash) and not user.password_hash.startswith("!")


def _build_login_response(user: User) -> LoginResponse:
    """按用户信息签发 JWT 双 Token 并组装登录响应。"""
    token_data = {"user_id": user.id, "role": user.role}
    return LoginResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        user_id=user.id,
        name=user.name,
        role=user.role,
        phone=user.phone,
        email=user.email,
        avatar_url=user.avatar_url,
    )


async def login_with_code(db: AsyncSession, req: CodeLoginRequest) -> LoginResponse:
    """手机号 + 验证码登录；手机号未注册时自动建号（免密码）。

    Raises:
        ValueError: 验证码错误/过期，或账号被禁用
    """
    verify_code(req.phone, req.code)

    user = await find_user_by_phone(db, req.phone)
    if user is None:
        user = User(
            phone=req.phone,
            email=None,
            password_hash=_CODE_LOGIN_PASSWORD_HASH,
            name=f"用户{req.phone[-4:]}",
            role="blind",
            status="active",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("验证码登录自动建号 user_id=%s", user.id)

    if user.status != "active":
        raise ValueError("账号已被禁用")

    return _build_login_response(user)


async def refresh_user_token(db: AsyncSession, req: RefreshRequest) -> RefreshResponse:
    """校验 refresh token 并签发新的 JWT 双 Token。"""
    settings = get_settings()
    try:
        payload = jwt.decode(
            req.refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise ValueError("登录已过期，请重新登录")
    except jwt.InvalidTokenError:
        raise ValueError("无效的认证凭证")

    user_id = payload.get("user_id")
    token_type = payload.get("type")
    if user_id is None or token_type != "refresh":
        raise ValueError("无效的认证凭证")

    # 用户必须仍存在且可用
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError("用户不存在")
    if user.status != "active":
        raise ValueError("账号已被禁用")

    token_data = {"user_id": user.id, "role": user.role}
    return RefreshResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )

"""认证请求/响应 Schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ===== 注册 =====

class RegisterRequest(BaseModel):
    """注册请求体。"""
    phone: str = Field(..., min_length=1, max_length=20, description="手机号")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    name: str = Field(..., min_length=1, max_length=50, description="姓名")
    role: str = Field(default="blind", description="角色: blind/family/admin")


class RegisterResponse(BaseModel):
    """注册成功响应。"""
    user_id: int
    name: str
    role: str


# ===== 登录 =====

class LoginRequest(BaseModel):
    """登录请求体。支持手机号或邮箱登录。"""
    account: str = Field(..., min_length=1, description="手机号或邮箱")
    password: str = Field(..., min_length=1, description="密码")


class LoginResponse(BaseModel):
    """登录成功响应。"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    name: str
    role: str
    phone: str | None = None
    email: str | None = None
    avatar_url: str | None = None

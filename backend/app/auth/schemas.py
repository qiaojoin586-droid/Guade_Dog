"""认证请求/响应 Schema。"""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# ===== 注册 =====

_PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
_EMAIL_RE = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")


class RegisterRequest(BaseModel):
    """注册请求体。手机号与邮箱至少提供一个。"""
    phone: Optional[str] = Field(default=None, max_length=20, description="手机号")
    email: Optional[str] = Field(default=None, max_length=120, description="邮箱")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    name: str = Field(..., min_length=1, max_length=50, description="姓名")
    # 注意：admin 不允许通过注册接口自提权，由数据库/管理端创建
    role: Literal["blind", "family"] = Field(default="blind", description="角色: blind/family")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """校验手机号格式。"""
        if v is not None:
            if not _PHONE_RE.match(v):
                raise ValueError("手机号格式不正确")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """校验邮箱格式。"""
        if v is not None:
            if not _EMAIL_RE.match(v):
                raise ValueError("邮箱格式不正确")
        return v

    @model_validator(mode="after")
    def check_identity(self) -> "RegisterRequest":
        """手机号与邮箱至少提供一个，否则无法登录。"""
        if not self.phone and not self.email:
            raise ValueError("手机号和邮箱至少填写一个")
        return self


class RegisterResponse(BaseModel):
    """注册成功响应。"""
    user_id: int
    name: str
    role: str


# ===== 登录 =====

class LoginRequest(BaseModel):
    """登录请求体。支持手机号或邮箱登录。"""
    account: str = Field(..., min_length=1, description="手机号或邮箱")
    password: str = Field(..., min_length=1, max_length=128, description="密码")


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


# ===== Token 刷新 =====

class RefreshRequest(BaseModel):
    """刷新 Token 请求体。"""
    refresh_token: str = Field(..., min_length=1, description="refresh token")


class RefreshResponse(BaseModel):
    """刷新 Token 成功响应。"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

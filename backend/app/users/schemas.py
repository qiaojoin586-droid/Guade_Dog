"""用户资料请求/响应 Schema。"""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class UserProfileResponse(BaseModel):
    """用户信息响应（GET /users/me）。"""

    user_id: int
    phone: Optional[str] = None
    email: Optional[str] = None
    name: str
    role: str
    status: str
    avatar_url: Optional[str] = None
    medical_notes: Optional[str] = None
    created_at: str
    updated_at: str


class UpdateProfileRequest(BaseModel):
    """更新用户资料请求体（PUT /users/me）。"""

    name: Optional[str] = Field(default=None, min_length=1, max_length=50, description="姓名")
    phone: Optional[str] = Field(default=None, min_length=1, max_length=20, description="手机号")
    email: Optional[str] = Field(default=None, max_length=120, description="邮箱")
    avatar_url: Optional[str] = Field(default=None, max_length=512, description="头像URL")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """校验手机号格式（允许空值表示不修改）。"""
        if v is not None and v != "":
            # 中国大陆手机号：1开头，11位数字
            if not re.match(r"^1[3-9]\d{9}$", v):
                raise ValueError("手机号格式不正确")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """校验邮箱格式。"""
        if v is not None and v != "":
            if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", v):
                raise ValueError("邮箱格式不正确")
        return v

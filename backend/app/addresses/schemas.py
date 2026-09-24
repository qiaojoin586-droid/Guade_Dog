"""常用地址请求/响应 Schema。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AddressCreate(BaseModel):
    """新增常用地址。"""

    label: str = Field(..., max_length=20, description="别名，如 家/公司/健身房")
    address: str = Field(..., max_length=255, description="详细地址")
    lat: Optional[float] = Field(default=None, description="纬度")
    lng: Optional[float] = Field(default=None, description="经度")
    is_default: bool = Field(default=False, description="是否设为默认地址")

    @field_validator("label", "address")
    @classmethod
    def not_blank(cls, v: str) -> str:
        """去空格并禁止空值。"""
        v = v.strip()
        if not v:
            raise ValueError("不能为空")
        return v


class AddressUpdate(BaseModel):
    """修改常用地址（字段均可选）。"""

    label: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = Field(default=None, max_length=255)
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_default: Optional[bool] = None

    @field_validator("label", "address")
    @classmethod
    def not_blank(cls, v: Optional[str]) -> Optional[str]:
        """去空格并禁止空值。"""
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("不能为空")
        return v


class AddressOut(BaseModel):
    """常用地址响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    address: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    is_default: bool = False
    created_at: datetime

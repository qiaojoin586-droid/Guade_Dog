"""Conversation 模块请求/响应 Schema。

骨架阶段为空，后续补充认证、对话等 Schema。
"""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """登录请求占位。"""
    # TODO: 补充字段
    pass


class LoginResponse(BaseModel):
    """登录响应占位。"""
    # TODO: 补充字段
    pass

"""统一错误码常量表。

按后端文档 §6.0 定义，4 个模块统一引用。
错误码格式：XXXXX，前两位为 HTTP 状态码段，后三位为业务编号。
"""

from __future__ import annotations

from typing import Any

# ===== 错误码常量 =====

ERR_INVALID_INPUT = 40001       # 参数/输入错误          → "没听清，请再说一次"
ERR_AUTH_REQUIRED = 40101       # 未登录                → "请先登录"
ERR_TOKEN_EXPIRED = 40102       # Token 过期            → "登录已过期，请重新登录"
ERR_NOT_FOUND = 40201           # 资源不存在            → "未找到，请换个说法"
ERR_BUSINESS_REJECT = 40301     # 业务拒绝              → "已收到您的求助，请等待响应"
ERR_EMERGENCY_INTERCEPT = 40300  # 紧急词拦截              → "请立即拨打120急救电话"
ERR_INTERNAL = 50001            # 内部错误              → "系统繁忙，请稍后重试"
ERR_EXT_TIMEOUT = 50011         # 外部服务超时          → "网络超时，正在切换离线模式"
ERR_EXT_UNAVAILABLE = 50021     # 外部服务不可用        → "服务暂不可用，请稍后再试"

# ===== 错误码 → 前端播报文案映射 =====

ERROR_VOICE_MAP: dict[int, str] = {
    ERR_INVALID_INPUT: "没听清，请再说一次",
    ERR_AUTH_REQUIRED: "请先登录",
    ERR_TOKEN_EXPIRED: "登录已过期，请重新登录",
    ERR_NOT_FOUND: "未找到，请换个说法",
    ERR_BUSINESS_REJECT: "已收到您的求助，请等待响应",
    ERR_EMERGENCY_INTERCEPT: "您描述的情况比较紧急，请立即拨打120急救电话，或请身边人协助就医",
    ERR_INTERNAL: "系统繁忙，请稍后重试",
    ERR_EXT_TIMEOUT: "网络超时，正在切换离线模式",
    ERR_EXT_UNAVAILABLE: "服务暂不可用，请稍后再试",
}


def build_error_response(
    code: int,
    message: str,
    detail: Any = None,
    request_id: str = "",
) -> dict:
    """构建统一格式的错误响应体。"""
    body: dict = {
        "code": code,
        "message": message,
        "request_id": request_id,
    }
    if detail is not None:
        body["detail"] = detail
    return body


def build_success_response(
    data: Any,
    request_id: str = "",
) -> dict:
    """构建统一格式的成功响应体。"""
    return {
        "code": 200,
        "data": data,
        "request_id": request_id,
    }

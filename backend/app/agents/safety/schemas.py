"""Safety 模块请求/响应 Schema。

本期能力: 药品识别(medicine) / 健康问答(health) / 钞票识别(currency)
SOS 相关 Schema 保留为下期占位。
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


# ===== 药品识别 =====

class MedicineInfo(BaseModel):
    """药品识别结果。unknown 表示该字段未能识别。"""

    name: str
    category: str = "unknown"
    indications: str = "unknown"
    dosage: str = "unknown"
    precautions: str = "unknown"


class MedicineOut(BaseModel):
    """药品识别响应。"""

    medicine: MedicineInfo
    unknown_fields: list[str] = Field(default_factory=list)
    tts_text: str


# ===== 健康问答 =====

class HealthAsk(BaseModel):
    """健康问答请求体。"""

    question: str = Field(..., min_length=1, max_length=500, description="健康问题")

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, v: str) -> str:
        """去除首尾空白；纯空白问题直接校验失败（避免误报 503 网络繁忙）。"""
        v = v.strip()
        if not v:
            raise ValueError("问题不能为空")
        return v


class HealthOut(BaseModel):
    """健康问答响应。emergency=True 表示命中紧急词拦截（急救指引）。"""

    answer: str
    tts_text: str
    emergency: bool = False
    code: int = 200


# ===== 钞票识别 =====

class CurrencyOut(BaseModel):
    """钞票识别响应。denomination=unknown 表示未确认面额。"""

    currency: str = "CNY"
    amount: int | None = None
    denomination: str
    confidence: float
    tts_text: str


# ===== SOS（下期占位） =====

class SOSRequest(BaseModel):
    """SOS 触发请求占位。"""

    # TODO: 补充字段
    pass


class SOSResponse(BaseModel):
    """SOS 响应占位。"""

    # TODO: 补充字段
    pass
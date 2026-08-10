"""Perception 模块请求/响应 Schema。

骨架阶段为空，后续补充天气、OCR、政策等 Schema。
"""

from pydantic import BaseModel


class WeatherResponse(BaseModel):
    """天气响应占位。"""
    # TODO: 补充字段
    pass


class OCRRequest(BaseModel):
    """OCR 请求占位。"""
    # TODO: 补充字段
    pass

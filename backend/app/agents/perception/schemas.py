"""Perception 模块请求/响应 Schema。

已实现: 天气查询(WeatherOut)。
待补充: OCR、提醒、政策问答等 Schema。
"""

from pydantic import BaseModel


class WeatherOut(BaseModel):
    """实时天气响应（与前端 WeatherInfo 对齐）。"""

    city: str                 # 城市名
    temperature: int          # 气温(℃)
    condition: str            # 天气现象("晴"/"多云"等)
    humidity: int | None = None   # 相对湿度(%)，源数据缺失时为 None
    uv_index: int | None = None   # 紫外线指数，查询失败时为 None
    dressing_advice: str      # 穿衣建议
    tts_text: str             # 可直接播报的文本


class OCRRequest(BaseModel):
    """OCR 请求占位。"""
    # TODO: 补充字段
    pass

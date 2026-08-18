"""Navigation 模块请求/响应 Schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ============================================================
# 当前位置（逆地理编码）
# ============================================================


class CoordsOut(BaseModel):
    """经纬度坐标。"""
    lat: float
    lng: float


class LocationOut(BaseModel):
    """当前位置查询响应。"""
    coords: CoordsOut | None = None  # IP 粗定位拿不到精确坐标时为 None，不返回伪坐标
    address: str           # "北京市东城区东华门街道天安门"
    city: str              # "北京市"
    source: str            # "gps" | "ip"
    tts_text: str          # 可直接播报的文本


# ============================================================
# 路线规划
# ============================================================


class RouteRequest(BaseModel):
    """路线规划请求。"""
    destination: str = Field(..., min_length=1, description="目的地地址或名称")
    origin: CoordsOut | None = Field(None, description="起点坐标，不传则用 IP 粗定位兜底")


class RouteStepOut(BaseModel):
    """单步导航指令。"""
    instruction: str       # "沿中关村大街向东北步行120米"
    distance_m: int
    duration_s: int


class RouteSummaryOut(BaseModel):
    """路线总览。"""
    distance_m: int
    duration_min: int      # 分钟（向上取整）
    start_address: str
    end_address: str


class RouteOut(BaseModel):
    """路线规划响应。"""
    summary: RouteSummaryOut
    steps: list[RouteStepOut]
    tts_text: str          # LLM 润色后的播报文案（失败则为原始拼接兜底）

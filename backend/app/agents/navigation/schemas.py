"""Navigation 模块请求/响应 Schema。

骨架阶段为空，后续补充导航、POI 等 Schema。
"""

from pydantic import BaseModel


class RouteRequest(BaseModel):
    """路线规划请求占位。"""
    # TODO: 补充字段
    pass


class RouteResponse(BaseModel):
    """路线规划响应占位。"""
    # TODO: 补充字段
    pass

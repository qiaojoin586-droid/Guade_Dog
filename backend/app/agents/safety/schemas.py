"""Safety 模块请求/响应 Schema。

骨架阶段为空，后续补充 SOS、药品识别等 Schema。
"""

from pydantic import BaseModel


class SOSRequest(BaseModel):
    """SOS 触发请求占位。"""
    # TODO: 补充字段
    pass


class SOSResponse(BaseModel):
    """SOS 响应占位。"""
    # TODO: 补充字段
    pass

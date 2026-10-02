"""Conversation 模块请求/响应 Schema。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CoordsInput(BaseModel):
    """浏览器 GPS 坐标(前端尽力获取,拿不到不传)。"""

    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    accuracy: float | None = Field(None, ge=0, description="定位精度(米),浏览器提供;越大越不可信")


class ChatRequest(BaseModel):
    """语音对话请求: ASR 识别出的文本进 LLM + 工具调用。"""

    text: str = Field(..., min_length=1, max_length=2000, description="用户语音识别文本")
    session_id: str = Field(default="", max_length=64, description="会话ID(预留多轮上下文)")
    coords: CoordsInput | None = Field(None, description="浏览器 GPS 坐标,供定位/导航类工具使用")


class CommandRequest(BaseModel):
    """语音指令请求（演示版规则大脑，不走 LLM）。

    trigger 用于前端事件触发，不需要说话：
    - shake      用户手机剧烈抖动（模拟遭遇危险）
    - sos_timeout 10 秒内未回应，自动求救
    - sos_cancel  用户明确说“不需要”
    """

    text: str = Field(default="", max_length=500, description="语音识别文本")
    trigger: Literal["", "shake", "sos_timeout", "sos_cancel"] = Field(
        default="", description="前端事件触发标识"
    )
    session_id: str = Field(default="", max_length=64, description="会话ID(预留多轮上下文)")
    coords: CoordsInput | None = Field(
        None, description="浏览器 GPS 坐标，供天气/定位类工具使用"
    )


class TTSRequest(BaseModel):
    """语音合成请求。"""

    text: str = Field(..., min_length=1, max_length=1000, description="要合成的文本")

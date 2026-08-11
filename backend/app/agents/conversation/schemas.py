"""Conversation 模块请求/响应 Schema。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """语音对话请求: ASR 识别出的文本进 LLM + 工具调用。"""

    text: str = Field(..., min_length=1, max_length=2000, description="用户语音识别文本")
    session_id: str = Field(default="", max_length=64, description="会话ID(预留多轮上下文)")


class TTSRequest(BaseModel):
    """语音合成请求。"""

    text: str = Field(..., min_length=1, max_length=1000, description="要合成的文本")

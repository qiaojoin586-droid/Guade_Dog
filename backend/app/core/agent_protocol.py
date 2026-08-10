"""★ Agent 调用协议（冻结契约）。

本文件为冻结契约，改动需 4 人集成评审。
由 Conversation 负责人维护，其余 3 个模块只依赖本文件中的类型定义。

参见设计方案 §2.3。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Agent 统一请求体。

    由 Orchestrator 构造并发送给目标 Agent。
    """

    session_id: str                                          # 会话ID
    user_id: str                                             # 用户ID
    intent: str                                              # Orchestrator(LLM) 解析出的意图
    params: dict = Field(default_factory=dict)               # 目的地、时间、图片URL等
    context: dict = Field(default_factory=dict)              # 位置、对话历史、语音原文等


class AgentResponse(BaseModel):
    """Agent 统一响应体。"""

    text: str                                                # 要播报的文本（统一由 Conversation TTS 播出）
    action: str | None = None                                # "navigate" | "trigger_sos" | ...
    data: dict | None = None                                 # 结构化结果（导航指令、药品信息等）
    needs_followup: bool = False                             # 是否需要 Orchestrator 追问澄清


class AgentError(BaseModel):
    """Agent 错误响应。"""

    code: str                                                # "timeout" | "low_confidence" | "service_unavailable"
    fallback_text: str                                       # 兜底播报文本（宁可说"不确定"，不要说错）

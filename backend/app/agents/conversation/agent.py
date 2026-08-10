"""Conversation Agent 实现。

实现 Agent 契约: handle(req: AgentRequest) -> AgentResponse
骨架阶段返回固定占位文本。
"""

from __future__ import annotations

from app.core.agent_protocol import AgentRequest, AgentResponse


class ConversationAgent:
    """对话 Agent —— 语音交互入口与公共 TTS 播报。"""

    async def handle(self, req: AgentRequest) -> AgentResponse:
        """处理请求，返回占位回复。

        TODO: 实现 ASR → 意图分类 → TTS 完整闭环。
        """
        return AgentResponse(
            text="语音对话功能开发中，请稍后再试",
            action=None,
            data=None,
            needs_followup=False,
        )

"""Perception Agent 实现。

实现 Agent 契约: handle(req: AgentRequest) -> AgentResponse
骨架阶段返回固定占位文本。
"""

from __future__ import annotations

from app.core.agent_protocol import AgentRequest, AgentResponse


class PerceptionAgent:
    """感知 Agent —— 生活服务与政策咨询。"""

    async def handle(self, req: AgentRequest) -> AgentResponse:
        """处理请求，返回占位回复。

        TODO: 实现天气查询、OCR、物体识别、提醒、政策问答。
        """
        return AgentResponse(
            text="生活服务功能开发中，请稍后再试",
            action=None,
            data=None,
            needs_followup=False,
        )

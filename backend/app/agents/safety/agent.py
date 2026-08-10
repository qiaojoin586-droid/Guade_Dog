"""Safety Agent 实现。

实现 Agent 契约: handle(req: AgentRequest) -> AgentResponse
骨架阶段返回固定占位文本。
"""

from __future__ import annotations

from app.core.agent_protocol import AgentRequest, AgentResponse


class SafetyAgent:
    """安全 Agent —— SOS 求救与健康防护。"""

    async def handle(self, req: AgentRequest) -> AgentResponse:
        """处理请求，返回占位回复。

        TODO: 实现 SOS 触发、位置追踪、药品识别、健康问答。
        """
        return AgentResponse(
            text="安全功能开发中，请稍后再试",
            action=None,
            data=None,
            needs_followup=False,
        )

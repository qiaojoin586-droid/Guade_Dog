"""Navigation Agent 实现。

实现 Agent 契约: handle(req: AgentRequest) -> AgentResponse
骨架阶段返回固定占位文本。
"""

from __future__ import annotations

from app.core.agent_protocol import AgentRequest, AgentResponse


class NavigationAgent:
    """导航 Agent —— 路径规划与障碍物检测。"""

    async def handle(self, req: AgentRequest) -> AgentResponse:
        """处理请求，返回占位回复。

        TODO: 实现路径规划、障碍物检测、安全通行判断。
        """
        return AgentResponse(
            text="导航功能开发中，请稍后再试",
            action=None,
            data=None,
            needs_followup=False,
        )

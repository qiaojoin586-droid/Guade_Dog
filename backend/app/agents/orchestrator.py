"""Orchestrator — LLM 路由核心。

归属: Conversation 负责人（人A）
职责: 接收用户意图，路由到对应的 Agent 模块。

骨架阶段: 规则路由表占位（intent 字符串 → 模块实例映射），LLM 判断留 TODO。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.core.agent_protocol import AgentRequest, AgentResponse

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# 意图 → 模块映射表（骨架阶段硬编码，后续由 LLM 动态判断）
INTENT_ROUTING: dict[str, str] = {
    "chat": "conversation",
    "navigation": "navigation",
    "location": "navigation",
    "sos": "safety",
    "weather": "perception",
    "ocr": "perception",
    "vision": "perception",
    "reminder": "perception",
    "policy": "perception",
    "health": "safety",
    "medicine": "safety",
    "currency": "safety",
}


class Orchestrator:
    """LLM 路由核心，负责意图判断与 Agent 分发。"""

    def __init__(self) -> None:
        self._agents: dict[str, object] = {}
        self._init_agents()

    def _init_agents(self) -> None:
        """初始化 4 个 Agent 实例。"""
        from app.agents.conversation.agent import ConversationAgent
        from app.agents.navigation.agent import NavigationAgent
        from app.agents.safety.agent import SafetyAgent
        from app.agents.perception.agent import PerceptionAgent

        self._agents["conversation"] = ConversationAgent()
        self._agents["navigation"] = NavigationAgent()
        self._agents["safety"] = SafetyAgent()
        self._agents["perception"] = PerceptionAgent()

    async def route(self, req: AgentRequest) -> AgentResponse:
        """根据意图路由到对应 Agent。

        骨架阶段使用规则路由表；后续接入 LLM 进行动态意图判断。
        """
        # TODO: 接入 LLM 进行意图分类，替代硬编码路由表
        module_name = INTENT_ROUTING.get(req.intent, "conversation")
        agent = self._agents.get(module_name)

        if agent is None:
            logger.warning("未找到模块 [%s]，回退到 conversation", module_name)
            agent = self._agents["conversation"]

        return await agent.handle(req)

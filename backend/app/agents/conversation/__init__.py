"""Conversation Agent 模块。

归属: 人A（兼任 Orchestrator）
职责: ASR/TTS、唤醒词、对话管理、认证、家属绑定。
"""

from app.agents.conversation.agent import ConversationAgent

__all__ = ["ConversationAgent"]

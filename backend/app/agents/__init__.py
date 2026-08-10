"""Agent 模块注册表。

提供 Orchestrator 单例入口。
"""

from __future__ import annotations

from app.agents.orchestrator import Orchestrator

_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    """获取 Orchestrator 单例。"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator

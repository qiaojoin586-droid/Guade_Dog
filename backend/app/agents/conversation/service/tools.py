"""工具注册表 —— LLM 工具调用的预留接口(★核心预留点)。

每个工具 = ToolSpec(name, description, params_schema, agent_module, handler):
  * description / params_schema 动态拼进 LLM 系统提示词,让 LLM 选工具、填参数;
  * handler 负责执行。当前全部挂 _log_only 占位(结构化日志输出);
  * agent_module 对应 orchestrator.INTENT_ROUTING 的模块名,真实实现时由它
    路由到各 Agent(构造 AgentRequest 调 orchestrator.route())。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

# async (params, context, spec) -> dict,结果最终包成 AgentResponse
ToolHandler = Callable[[dict, dict, "ToolSpec"], Awaitable[dict]]


@dataclass(frozen=True)
class ToolSpec:
    name: str                          # 工具名,如 "navigation.start"
    description: str                   # 给 LLM 看的说明
    params_schema: dict[str, Any]      # 参数 JSON Schema(给 LLM 看)
    agent_module: str                  # 对应 Agent 模块(navigation/safety/perception/...)
    handler: ToolHandler               # 执行入口(当前占位)


async def _log_only(params: dict, context: dict, spec: "ToolSpec") -> dict:
    """占位 handler: 结构化日志输出,预留真实实现入口。

    真实实现时替换为: 构造 AgentRequest 调 orchestrator.route(),
    或直接调用真实服务。返回结构保持 dict。
    """
    # 识别文本属隐私,不落日志原文,只记录长度
    safe_context = {k: v for k, v in context.items() if k != "transcript"}
    if "transcript" in context:
        safe_context["transcript_len"] = len(context["transcript"])
    logger.info(
        "【工具调用·占位】tool=%s agent_module=%s params=%s context=%s",
        spec.name,
        spec.agent_module,
        json.dumps(params, ensure_ascii=False),
        json.dumps(safe_context, ensure_ascii=False),
    )
    return {"status": "not_implemented", "tool": spec.name}


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "navigation.start": ToolSpec(
        name="navigation.start",
        description="规划前往某地的步行导航路线。用户表达出行、去某地、怎么走等意图时使用。",
        params_schema={
            "type": "object",
            "properties": {"destination": {"type": "string", "description": "目的地名称或地址"}},
            "required": ["destination"],
        },
        agent_module="navigation",
        handler=_log_only,
    ),
    "safety.sos": ToolSpec(
        name="safety.sos",
        description="触发紧急求救(SOS),通知家属与救援。用户表达危险、求助、救命等意图时使用。",
        params_schema={
            "type": "object",
            "properties": {"location": {"type": "string", "description": "当前位置描述,可选"}},
        },
        agent_module="safety",
        handler=_log_only,
    ),
    "perception.weather": ToolSpec(
        name="perception.weather",
        description="查询天气情况。用户询问天气、温度、是否下雨等意图时使用。",
        params_schema={
            "type": "object",
            "properties": {"city": {"type": "string", "description": "城市名,可选,默认使用定位"}},
        },
        agent_module="perception",
        handler=_log_only,
    ),
    "perception.reminder": ToolSpec(
        name="perception.reminder",
        description="设置语音提醒。用户表达提醒我、别忘了等意图时使用。",
        params_schema={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "提醒内容"},
                "time": {"type": "string", "description": "提醒时间,如 明天上午9点"},
            },
            "required": ["content"],
        },
        agent_module="perception",
        handler=_log_only,
    ),
}


async def dispatch(tool: str, params: dict, context: dict) -> dict | None:
    """分发工具调用。未知工具返回 None,调用方回退纯聊天。"""
    spec = TOOL_REGISTRY.get(tool)
    if spec is None:
        logger.warning("未知工具: %s", tool)
        return None
    return await spec.handler(params, context, spec)

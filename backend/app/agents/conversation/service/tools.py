"""工具注册表 —— LLM 工具调用的注册与分发(单 LLM 调度核心)。

每个工具 = ToolSpec(name, description, params_schema, agent_module, handler):
  * description / params_schema 动态拼进 LLM 系统提示词,让 LLM 选工具、填参数;
  * handler 负责执行: 构造 AgentRequest 调 orchestrator.route() 路由到对应 Agent 模块
    (Agent 模块是平级工具,互不调用,全部由调度 LLM 选择);
  * agent_module 对应 orchestrator.INTENT_ROUTING 的模块名;
  * 全部工具已接真实 handler;新增工具未实现时先挂 _log_only 占位。
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


async def _route_to_agent(params: dict, context: dict, intent: str) -> dict:
    """真实工具分发: 构造 AgentRequest 走 orchestrator 路由到对应 Agent。

    返回 {text, data?, action?}: text 为可播报文案(chat.py 会拼进回复),
    data/action 原样上送前端。
    """
    from app.agents import get_orchestrator
    from app.core.agent_protocol import AgentRequest

    orchestrator = get_orchestrator()
    resp = await orchestrator.route(
        AgentRequest(
            session_id=context.get("session_id", ""),
            user_id=context.get("user_id", ""),
            intent=intent,
            params=params,
            context=context,
        )
    )
    result: dict = {"text": resp.text}
    if resp.data:
        result["data"] = resp.data
    if resp.action:
        result["action"] = resp.action
    return result


def _make_agent_handler(intent: str) -> ToolHandler:
    """按意图生成真实 handler(闭包绑定 intent)。"""

    async def handler(params: dict, context: dict, spec: "ToolSpec") -> dict:
        return await _route_to_agent(params, context, intent)

    return handler


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
        handler=_make_agent_handler("navigation"),  # 已接真实导航服务
    ),
    "navigation.location": ToolSpec(
        name="navigation.location",
        description="查询用户当前所在位置/地址。用户询问我在哪、我的位置、当前位置、定位等意图时使用。",
        params_schema={"type": "object", "properties": {}},
        agent_module="navigation",
        handler=_make_agent_handler("location"),  # 已接真实定位服务
    ),
    "navigation.distance": ToolSpec(
        name="navigation.distance",
        description="查询当前位置到某地的距离(远近)。用户询问'有多远''离我多远''距离多远'等远近问题时使用。只回答距离,不规划路线。",
        params_schema={
            "type": "object",
            "properties": {"destination": {"type": "string", "description": "目的地名称或地址"}},
            "required": ["destination"],
        },
        agent_module="navigation",
        handler=_make_agent_handler("distance"),  # 已接真实距离查询服务
    ),
    "safety.sos": ToolSpec(
        name="safety.sos",
        description="触发紧急求救(SOS)。用户表达危险、求助、救命、摔倒等紧急意图时使用。",
        params_schema={
            "type": "object",
            "properties": {"location": {"type": "string", "description": "当前位置描述,可选"}},
        },
        agent_module="safety",
        handler=_make_agent_handler("sos"),  # 已接真实求救服务
    ),
    "perception.weather": ToolSpec(
        name="perception.weather",
        description="查询天气情况。用户询问天气、温度、是否下雨等意图时使用。用户没有说具体城市时,city 参数留空即可,工具会自动定位用户当前位置并查询当地天气,不要反问用户城市。",
        params_schema={
            "type": "object",
            "properties": {"city": {"type": "string", "description": "城市名;用户未指定时留空,工具自动使用当前位置"}},
        },
        agent_module="perception",
        handler=_make_agent_handler("weather"),  # 已接真实天气服务
    ),
    "perception.reminder": ToolSpec(
        name="perception.reminder",
        description="设置语音提醒。用户表达提醒我、别忘了等意图时使用。",
        params_schema={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "提醒内容"},
                "time": {"type": "string", "description": "提醒时间,如 半小时后、明天上午9点"},
            },
            "required": ["content"],
        },
        agent_module="perception",
        handler=_make_agent_handler("reminder"),  # 已接真实提醒服务
    ),
}


async def dispatch(tool: str, params: dict, context: dict) -> dict | None:
    """分发工具调用。未知工具返回 None,调用方回退纯聊天。"""
    spec = TOOL_REGISTRY.get(tool)
    if spec is None:
        logger.warning("未知工具: %s", tool)
        return None
    return await spec.handler(params, context, spec)

"""语音文本 → LLM → 工具分发 编排层。

调用链:
  transcript ──llm.complete(json_mode)──> {tool, params, chat_reply}
                                        └─tools.dispatch──> AgentResponse

LLM 输出非法时重试 1 次,仍失败则兜底回复(宁可不执行,不可说错)。
"""

from __future__ import annotations

import json
import logging
import re

from app.agents.conversation.service.tools import TOOL_REGISTRY, dispatch
from app.core import llm
from app.core.agent_protocol import AgentResponse
from app.core.llm import LLMError

logger = logging.getLogger(__name__)


def _extract_json(raw: str) -> dict:
    """容错解析 LLM 的 JSON 输出。

    兼容: 纯 JSON、带 ```json 围栏、前后有解释性文本等情况。
    无法提取时抛 json.JSONDecodeError,由调用方兜底。
    """
    text = raw.strip()
    # 1) 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 2) 去掉 markdown 代码围栏后解析
    fenced = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text).strip()
    if fenced and fenced != text:
        try:
            return json.loads(fenced)
        except json.JSONDecodeError:
            pass
    # 3) 提取第一个 { ... } 块
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise json.JSONDecodeError("未找到 JSON 对象", raw, 0)

_SYSTEM_TEMPLATE = """你是导盲AI智能体的语音交互助手。根据用户的语音识别文本,判断用户意图并选择最合适的工具。

可用工具列表:
{TOOLS}

输出要求: 只输出一个 JSON 对象,不要输出任何其他内容。格式:
{{"tool": "工具名,不需要调用工具时填 null", "params": {{工具参数}}, "chat_reply": "给用户的自然中文回复,简短口语化"}}

注意事项:
1. 工具参数必须符合该工具的 params_schema。
2. 调用工具时,chat_reply 只写简短的衔接语(如"好的"、"正在为您查询"),
   不要自行编造工具的执行结果——具体结果会由工具返回并追加播报。
   例: 设提醒时写"好的"即可,不要写"已为您设置…提醒";
   求救时写"正在为您求救",不要写急救指引;查天气时写"正在为您查询",不要编天气数据。
3. 不要调用工具时,chat_reply 直接回答用户。
4. 用户问天气/位置但没说具体城市时,把相应参数留空,工具会自动定位,
   不要反问用户城市,也不要跳过工具自己猜测位置。"""


def _build_tools_prompt() -> str:
    """从注册表动态生成给 LLM 的工具清单。"""
    lines = []
    for spec in TOOL_REGISTRY.values():
        lines.append(
            f"- {spec.name}: {spec.description} "
            f"参数Schema: {json.dumps(spec.params_schema, ensure_ascii=False)}"
        )
    return "\n".join(lines)


async def chat(
    transcript: str,
    session_id: str,
    user_id: str,
    coords: dict | None = None,
) -> AgentResponse:
    """识别文本进 LLM,解析工具调用并分发,返回给用户的回复。

    Args:
        transcript: ASR 识别出的用户语音文本
        session_id: 会话ID(预留多轮上下文)
        user_id: 用户ID(由 API 层从 JWT 解析后传入)
        coords: 浏览器 GPS 坐标 {"lat":.., "lng":..},供定位/导航工具使用
    """
    system = _SYSTEM_TEMPLATE.replace("{TOOLS}", _build_tools_prompt())
    context = {
        "transcript": transcript,
        "session_id": session_id,
        "user_id": user_id,
    }
    if coords:
        context["coords"] = coords

    for attempt in (1, 2):  # 失败重试一次
        try:
            raw = await llm.complete(transcript, json_mode=True, system=system)
            parsed = _extract_json(raw)
            tool = parsed.get("tool") or None
            params = parsed.get("params") or {}
            reply = (parsed.get("chat_reply") or "").strip()

            result = None
            if tool is not None:
                result = await dispatch(tool, params, context)
                if result is None:
                    logger.warning("LLM 选中未知工具 [%s],回退纯聊天", tool)
                    tool = None
                else:
                    tool_text = result.get("text") if isinstance(result, dict) else None
                    if isinstance(tool_text, str) and tool_text.strip():
                        tool_text = tool_text.strip()
                        if len(reply) <= 6:
                            # chat_reply 只是纯衔接语("好的"等),直接用工具结果播报
                            reply = tool_text
                        else:
                            # 工具返回了真实结果文本(如天气数据),拼接到回复后一起播报
                            sep = "" if reply.rstrip().endswith(("。", "！", "？", "...")) else "。"
                            reply = f"{reply}{sep}{tool_text}"
                    elif not reply:
                        reply = f"好的,收到: {tool}"

            if not reply:
                reply = "好的,我知道了"
            logger.info(
                "对话处理完成 tool=%s text_len=%d", tool, len(transcript)
            )  # 不落识别文本原文
            data = {"tool_called": tool} if tool else None
            if result and isinstance(result, dict) and result.get("data"):
                data = data or {}
                data["tool_data"] = result["data"]
            if result and isinstance(result, dict) and result.get("action"):
                data = data or {}
                data["action"] = result["action"]
            return AgentResponse(
                text=reply,
                action=None,
                data=data,
                needs_followup=False,
            )
        except (LLMError, json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.warning("LLM 处理失败(第 %d 次): %s", attempt, exc)
            continue

    logger.error("LLM 两次尝试均失败,返回兜底回复")
    return AgentResponse(
        text="抱歉,我没太理解,请换个说法试试",
        action=None,
        data=None,
        needs_followup=False,
    )

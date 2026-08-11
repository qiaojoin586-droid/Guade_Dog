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

工具参数必须符合该工具的 params_schema。"""


def _build_tools_prompt() -> str:
    """从注册表动态生成给 LLM 的工具清单。"""
    lines = []
    for spec in TOOL_REGISTRY.values():
        lines.append(
            f"- {spec.name}: {spec.description} "
            f"参数Schema: {json.dumps(spec.params_schema, ensure_ascii=False)}"
        )
    return "\n".join(lines)


async def chat(transcript: str, session_id: str, user_id: str = "anonymous") -> AgentResponse:
    """识别文本进 LLM,解析工具调用并分发,返回给用户的回复。

    Args:
        transcript: ASR 识别出的用户语音文本
        session_id: 会话ID(预留多轮上下文)
        user_id: 用户ID(预留,后续接认证)
    """
    system = _SYSTEM_TEMPLATE.replace("{TOOLS}", _build_tools_prompt())
    context = {
        "transcript": transcript,
        "session_id": session_id,
        "user_id": user_id,
    }

    for attempt in (1, 2):  # 失败重试一次
        try:
            raw = await llm.complete(transcript, json_mode=True, system=system)
            parsed = _extract_json(raw)
            tool = parsed.get("tool") or None
            params = parsed.get("params") or {}
            reply = (parsed.get("chat_reply") or "").strip()

            if tool is not None:
                result = await dispatch(tool, params, context)
                if result is None:
                    logger.warning("LLM 选中未知工具 [%s],回退纯聊天", tool)
                    tool = None
                elif not reply:
                    reply = f"好的,收到: {tool}"

            if not reply:
                reply = "好的,我知道了"
            logger.info(
                "对话处理完成 tool=%s text_len=%d", tool, len(transcript)
            )  # 不落识别文本原文
            return AgentResponse(
                text=reply,
                action=None,
                data={"tool_called": tool} if tool else None,
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

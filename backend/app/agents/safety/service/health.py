"""健康问答服务（带安全护栏）。

- 紧急词前置拦截：命中直接返回急救指引，不走 LLM（不受 LLM 可用性影响）；
- system 提示词：不诊断、不推荐处方药、紧急建议就医；
- LLM 失败重试 1 次。
"""

from __future__ import annotations

import logging
import re

from app.core import llm
from app.core.errors import ERR_EMERGENCY_INTERCEPT

logger = logging.getLogger(__name__)

# 紧急关键词：命中即转急救指引（规则先于 LLM）
EMERGENCY_PATTERN = re.compile(
    r"拨打120|打120|急救|自杀|大出血|胸痛|呼吸困难|晕倒|昏迷|割腕|药物过量|没心跳|心脏骤停|窒息|触电|溺水|抽搐|中风|脑梗|心梗"
)

_HEALTH_SYSTEM = """你是健康咨询助手，面向视障用户，回答简洁口语化（优先 50 字以内）。
规则：
1. 不给出诊断结论，不推荐处方药；
2. 可给出一般性健康建议与就医建议；
3. 症状紧急（胸痛、呼吸困难、大出血、晕倒等）时，明确建议立即就医或拨打 120；
4. 结尾可提醒"如症状持续或加重，请及时就医"。"""

_EMERGENCY_GUIDANCE = "您描述的情况比较紧急，请立即停止当前活动，尽快拨打120急救电话，或请身边人协助就医。"


def is_emergency(question: str) -> bool:
    """判断问题是否命中紧急关键词。"""
    return bool(EMERGENCY_PATTERN.search(question or ""))


async def ask(question: str) -> dict:
    """健康问答，返回 {answer, tts_text, emergency, code}。

    Raises:
        ValueError: 问题为空。
        llm.LLMError: LLM 调用失败（已重试 1 次）。
    """
    question = (question or "").strip()
    if not question:
        raise ValueError("问题不能为空")

    # 紧急词前置拦截（不走 LLM）
    if is_emergency(question):
        return {
            "answer": _EMERGENCY_GUIDANCE,
            "tts_text": _EMERGENCY_GUIDANCE,
            "emergency": True,
            "code": ERR_EMERGENCY_INTERCEPT,
        }

    answer = ""
    for attempt in (1, 2):  # 失败重试一次
        try:
            answer = await llm.complete(question, system=_HEALTH_SYSTEM, temperature=0.3)
            break
        except llm.LLMError as exc:
            logger.warning("健康问答 LLM 失败(第%d次): %s", attempt, exc)
            answer = ""

    if not answer:
        raise llm.LLMError("健康问答服务暂不可用")

    return {
        "answer": answer,
        "tts_text": answer,
        "emergency": False,
        "code": 200,
    }
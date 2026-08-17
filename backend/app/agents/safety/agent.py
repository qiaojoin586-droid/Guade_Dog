"""Safety Agent 实现。

实现 Agent 契约: handle(req: AgentRequest) -> AgentResponse
本期能力: 药品识别(medicine) / 健康问答(health) / 钞票识别(currency)
图片场景由工具链路以 base64 传入 params["image_base64"]。
"""

from __future__ import annotations

import base64
import binascii
import logging

from app.core import llm
from app.core.agent_protocol import AgentRequest, AgentResponse
from app.core.errors import ERR_EXT_UNAVAILABLE

from .service import currency, health, medicine
from .service.vision import VisionError

logger = logging.getLogger(__name__)

# 兜底文案（宁可说不确定/开发中，不说错）
_FALLBACK = "安全助手功能开发中，请稍后再试"


class SafetyAgent:
    """安全 Agent —— 药品识别 / 健康问答 / 钞票识别。"""

    async def handle(self, req: AgentRequest) -> AgentResponse:
        """按意图分发三个能力。"""
        intent = req.intent
        params = req.params or {}

        try:
            if intent == "health":
                return await self._health(params)
            if intent in ("medicine", "currency"):
                return await self._image_recognize(intent, params)
        except VisionError as exc:
            logger.warning("安全模块识别失败 code=%s detail=%s", exc.code, exc.detail or exc.message)
            return AgentResponse(
                text=exc.fallback_text,
                action=None,
                data={"code": exc.code},
                needs_followup=False,
            )
        except ValueError as exc:
            logger.warning("安全模块参数错误: %s", exc)
            return AgentResponse(
                text="请上传要识别的照片",
                action=None,
                data=None,
                needs_followup=False,
            )
        except Exception as exc:  # 统一兜底
            logger.exception("安全模块处理异常: %s", exc)
            return AgentResponse(
                text="系统繁忙，请稍后再试",
                action=None,
                data=None,
                needs_followup=False,
            )

        return AgentResponse(text=_FALLBACK, action=None, data=None, needs_followup=False)

    async def _health(self, params: dict) -> AgentResponse:
        """健康问答。"""
        question = (params.get("question") or "").strip()
        if not question:
            return AgentResponse(
                text="请说出您的健康问题",
                action=None,
                data=None,
                needs_followup=True,
            )
        try:
            result = await health.ask(question)
        except llm.LLMError as exc:
            logger.warning("健康问答 LLM 不可用: %s", exc)
            return AgentResponse(
                text="网络繁忙，请稍后再试",
                action=None,
                data={"code": ERR_EXT_UNAVAILABLE},
                needs_followup=False,
            )
        return AgentResponse(
            text=result["tts_text"],
            action=None,
            data=result,
            needs_followup=False,
        )

    async def _image_recognize(self, intent: str, params: dict) -> AgentResponse:
        """药品/钞票图片识别（base64 透传）。"""
        image_b64 = (params.get("image_base64") or "").strip()
        if not image_b64:
            return AgentResponse(
                text="请上传要识别的照片",
                action=None,
                data=None,
                needs_followup=True,
            )
        try:
            image_bytes = base64.b64decode(image_b64)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("图片 base64 无效") from exc

        if intent == "medicine":
            result = await medicine.recognize(image_bytes)
        else:
            result = await currency.recognize(image_bytes)

        return AgentResponse(
            text=result["tts_text"],
            action=None,
            data=result,
            needs_followup=False,
        )
"""钞票识别服务。

识别人民币纸币面额（1/5/10/20/50/100 元）。
置信度 < 0.7 或面额不确定时，不播报具体面额（宁可不确定，不可说错）。
"""

from __future__ import annotations

from .vision import recognize_image

CONFIDENCE_THRESHOLD = 0.7
_DENOMINATIONS = {"1元", "5元", "10元", "20元", "50元", "100元"}

_CURRENCY_PROMPT = """你是人民币面额识别器。请识别图片中纸币的面额，只输出 JSON，不要输出其他内容。
JSON 字段：
- denomination: 纸币面额，只能取 "1元"/"5元"/"10元"/"20元"/"50元"/"100元" 之一；不确定时写 "unknown"
- confidence: 置信度（0~1 的浮点数）
禁止编造面额。"""


async def recognize(image_bytes: bytes) -> dict:
    """识别钞票面额，返回 {currency, amount, denomination, confidence, tts_text}。

    Raises:
        VisionError: 视觉识别失败。
    """
    raw = await recognize_image(image_bytes, _CURRENCY_PROMPT)

    denomination = str(raw.get("denomination") or "").strip()
    try:
        confidence = float(raw.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0.0

    # 低置信度 / 未知面额 → 不播报具体金额
    if denomination not in _DENOMINATIONS or confidence < CONFIDENCE_THRESHOLD:
        return {
            "currency": "CNY",
            "amount": None,
            "denomination": "unknown",
            "confidence": confidence,
            "tts_text": "无法确认面额，请他人协助",
        }

    amount = int(denomination[:-1])  # "50元" -> 50
    return {
        "currency": "CNY",
        "amount": amount,
        "denomination": denomination,
        "confidence": confidence,
        "tts_text": f"这是一张{denomination}",
    }
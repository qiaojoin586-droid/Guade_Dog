"""药品识别服务。

拍照药盒/药瓶 → 千问 VL 结构化识别 → 播报文案（含免责声明）。
图片仅在内存处理，不落盘、不落日志。
"""

from __future__ import annotations

from .vision import ERR_RECOGNITION_FAILED, VisionError, recognize_image

# 免责声明：医疗场景红线，播报文案必带
DISCLAIMER = "以上为AI识别结果，仅供参考，请以说明书和医嘱为准"

_MEDICINE_PROMPT = """你是药品信息解读助手。请识别图片中药盒/药瓶上的信息，只输出 JSON，不要输出其他内容。
JSON 字段：
- name: 药品名称（string）
- category: 药品类别或生产厂家（string，不确定写 "unknown"）
- indications: 适应症（string，不确定写 "unknown"）
- dosage: 用法用量（string，不确定写 "unknown"）
- precautions: 注意事项/禁忌（string，不确定写 "unknown"）
信息不确定的字段一律写 "unknown"，禁止编造。"""


# 视为"未识别"的输出变体（英文 + 中文常见说法），禁止当有效内容播报
_UNKNOWN_VALUES = {"unknown", "未知", "不详", "无法确定", "无法确认", "无法识别", "待确认", "暂无"}


def _field(raw: dict, key: str) -> str:
    """提取字符串字段，规范化 unknown 及中文变体。"""
    val = raw.get(key)
    if isinstance(val, str):
        val = val.strip()
        if not val or val.lower() in _UNKNOWN_VALUES or val in _UNKNOWN_VALUES:
            return ""
        return val
    return ""


async def recognize(image_bytes: bytes) -> dict:
    """识别药品信息，返回 {medicine, unknown_fields, tts_text}。

    Raises:
        VisionError: 视觉识别失败（含未识别到药品名）。
    """
    raw = await recognize_image(image_bytes, _MEDICINE_PROMPT)

    medicine = {
        "name": _field(raw, "name"),
        "category": _field(raw, "category"),
        "indications": _field(raw, "indications"),
        "dosage": _field(raw, "dosage"),
        "precautions": _field(raw, "precautions"),
    }
    unknown_fields = [k for k, v in medicine.items() if not v]

    if not medicine["name"]:
        raise VisionError(
            ERR_RECOGNITION_FAILED,
            "未识别到药品名称",
            "识别失败，请换个角度重新拍摄",
        )

    # 播报：名称 + 适应症 + 用法用量 + 免责声明（不确定字段如实不播）
    parts = [f"识别到{medicine['name']}"]
    if medicine["indications"]:
        parts.append(f"用于{medicine['indications']}")
    if medicine["dosage"]:
        parts.append(f"用法用量{medicine['dosage']}")
    tts_text = "，".join(parts) + "。" + DISCLAIMER

    return {
        "medicine": medicine,
        "unknown_fields": unknown_fields,
        "tts_text": tts_text,
    }
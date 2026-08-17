"""视觉识别服务 —— 图片校验/压缩 → base64 → 千问 VL 多模态请求 → JSON 容错解析。

安全模块三个能力（药品/钞票）共用。
图片仅在内存处理：不落盘、不落日志、不写识别原文。
"""

from __future__ import annotations

import json
import logging
import re

import httpx

from app.config import get_settings
from app.utils.image import MAX_UPLOAD_BYTES, ImageValidationError, preprocess_image, to_base64_data_url

logger = logging.getLogger(__name__)

DASHSCOPE_COMPAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
VISION_TIMEOUT = 30.0

# 统一错误码（与 app/core/errors.py 保持一致）
ERR_IMG_INVALID = 40001          # 无图片/格式错/超限
ERR_RECOGNITION_FAILED = 40200   # 识别不出内容/解析失败
ERR_VISION_UNAVAILABLE = 50020   # 视觉模型不可用/额度耗尽


class VisionError(Exception):
    """视觉识别失败，携带统一错误码与兜底播报文案。

    detail 仅用于日志，绝不返回给前端。
    """

    def __init__(self, code: int, message: str, fallback_text: str, *, detail: str = ""):
        super().__init__(message)
        self.code = code
        self.message = message
        self.fallback_text = fallback_text
        self.detail = detail


def _extract_json(raw: str) -> dict:
    """容错解析 LLM 的 JSON 输出（纯 JSON / ```json 围栏 / 前后解释文本）。"""
    text = raw.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fenced = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", text).strip()
    if fenced and fenced != text:
        try:
            return json.loads(fenced)
        except json.JSONDecodeError:
            pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise json.JSONDecodeError("未找到 JSON 对象", raw, 0)


async def recognize_image(image_bytes: bytes, instruction: str) -> dict:
    """对图片执行视觉识别，返回结构化 JSON。

    Args:
        image_bytes: 原始图片字节（jpg/png）
        instruction: 给模型的指令（含输出 JSON 约束）

    Returns:
        解析后的 dict

    Raises:
        VisionError: 携带统一错误码（40001 / 40200 / 50020）。
    """
    settings = get_settings()
    api_key = settings.DASHSCOPE_API_KEY
    if not api_key:
        raise VisionError(
            ERR_VISION_UNAVAILABLE,
            "DASHSCOPE_API_KEY 未配置",
            "图像识别服务暂不可用，请稍后再试",
            detail="DASHSCOPE_API_KEY not configured",
        )

    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise VisionError(ERR_IMG_INVALID, "图片超过 10MB 上限", "请拍摄药盒或钞票的照片")

    # 校验 + 压缩 + base64（纯内存）
    try:
        processed = preprocess_image(image_bytes)
    except ImageValidationError as exc:
        raise VisionError(ERR_IMG_INVALID, str(exc), "请拍摄药盒或钞票的照片") from exc
    data_url = to_base64_data_url(processed, mime="jpeg")

    # 千问 VL（OpenAI 兼容接口）多模态请求
    payload = {
        "model": settings.DASHSCOPE_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": instruction},
                ],
            }
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with httpx.AsyncClient(timeout=VISION_TIMEOUT) as client:
            resp = await client.post(DASHSCOPE_COMPAT_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        raw_content = data["choices"][0]["message"]["content"]
        if isinstance(raw_content, str):
            content = raw_content.strip()
        elif isinstance(raw_content, list):
            # omni 类模型返回分段列表：取全部 text 段拼接；无文本段按识别失败处理
            parts = [
                p.get("text", "")
                for p in raw_content
                if isinstance(p, dict) and p.get("type") == "text"
            ]
            content = "".join(parts).strip()
            if not content:
                raise ValueError("视觉响应 content 列表无文本段")
        else:
            raise TypeError("视觉响应 content 类型不支持")
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500]
        if "AllocationQuota" in body or exc.response.status_code == 429:
            logger.warning("视觉模型额度不足: status=%s body=%s", exc.response.status_code, body)
            raise VisionError(
                ERR_VISION_UNAVAILABLE, "视觉模型额度不足", "图像识别服务暂不可用，请稍后再试", detail=body
            ) from exc
        logger.warning("视觉请求失败: status=%s body=%s", exc.response.status_code, body)
        raise VisionError(
            ERR_VISION_UNAVAILABLE,
            f"视觉请求失败({exc.response.status_code})",
            "图像识别服务暂不可用，请稍后再试",
            detail=body,
        ) from exc
    except httpx.HTTPError as exc:
        logger.warning("视觉请求网络错误: %s", exc)
        raise VisionError(
            ERR_VISION_UNAVAILABLE, "视觉请求网络错误", "图像识别服务暂不可用，请稍后再试", detail=str(exc)
        ) from exc
    except (KeyError, IndexError, ValueError, AttributeError, TypeError) as exc:
        logger.warning("视觉响应结构解析失败: %s", exc)
        raise VisionError(
            ERR_RECOGNITION_FAILED, "视觉响应结构解析失败", "识别失败，请换个角度重新拍摄", detail=str(exc)
        ) from exc

    # JSON 容错解析（不记录识别原文，只记长度）
    try:
        result = _extract_json(content)
    except json.JSONDecodeError as exc:
        logger.warning("视觉 JSON 解析失败, raw_len=%d", len(content))
        raise VisionError(
            ERR_RECOGNITION_FAILED, "视觉 JSON 解析失败", "识别失败，请换个角度重新拍摄", detail="raw_len=%d" % len(content)
        ) from exc

    if not isinstance(result, dict):
        raise VisionError(ERR_RECOGNITION_FAILED, "视觉输出非 JSON 对象", "识别失败，请换个角度重新拍摄")

    return result
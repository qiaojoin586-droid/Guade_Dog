"""图片预处理工具。

提供图片缩放、裁剪、格式转换等通用操作。
"""

from __future__ import annotations

import base64
import io
import logging

logger = logging.getLogger(__name__)

# 图片上传上限 10MB（与 vision.py / safety api.py 共用）
MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024


class ImageValidationError(Exception):
    """图片校验失败（格式错误、超限等）。"""


def preprocess_image(image_bytes: bytes, max_size: int = 1024) -> bytes:
    """预处理图片（缩放、格式标准化）。

    Args:
        image_bytes: 原始图片字节。
        max_size: 长边最大像素，超过则等比缩放。

    Returns:
        处理后的 JPEG 图片字节。

    Raises:
        ImageValidationError: 输入不是有效图片。
    """
    if not image_bytes:
        raise ImageValidationError("图片数据为空")

    try:
        from PIL import Image
    except ImportError:
        # Pillow 未安装时跳过缩放，原样返回（生产环境应安装 Pillow）
        logger.warning("Pillow 未安装，跳过图片缩放处理")
        return image_bytes

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()  # 校验是否为有效图片
        img = Image.open(io.BytesIO(image_bytes))  # verify 后需重新打开
    except Exception as exc:
        raise ImageValidationError(f"无效的图片格式: {exc}") from exc

    # 等比缩放
    w, h = img.size
    if max(w, h) > max_size:
        ratio = max_size / max(w, h)
        new_w, new_h = int(w * ratio), int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)

    # 统一转 JPEG（去除 alpha 通道）
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def to_base64_data_url(image_bytes: bytes, mime: str = "jpeg") -> str:
    """将图片字节转为 base64 data URL（供多模态 API 使用）。

    Args:
        image_bytes: 图片字节。
        mime: MIME 类型简写，如 "jpeg" / "png"。

    Returns:
        "data:image/{mime};base64,{base64_str}"
    """
    mime_map = {"jpeg": "image/jpeg", "jpg": "image/jpeg", "png": "image/png"}
    content_type = mime_map.get(mime.lower(), f"image/{mime}")
    b64 = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{content_type};base64,{b64}"

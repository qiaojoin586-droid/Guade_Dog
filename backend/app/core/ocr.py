"""共享 OCR 推理接口。

负责人: Perception Agent（人D）
用途: 提供 OCR 文字识别的统一入口，供 Perception Agent 和 Safety Agent 调用。

通过阿里云 Qwen-VL 或 DashScope OCR API 实现，不加载本地模型。
骨架阶段只定义接口签名，不接真实 API。
"""

from __future__ import annotations


async def recognize(image_bytes: bytes) -> str:
    """对输入图像执行 OCR 文字识别。

    Args:
        image_bytes: 原始图像字节数据

    Returns:
        识别出的文字内容。
        骨架阶段返回空字符串。

    TODO: Perception 负责人接入 DashScope 视觉 API 实现。
    """
    # 占位实现
    return ""

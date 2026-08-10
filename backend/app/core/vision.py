"""共享视觉推理接口。

负责人: Navigation Agent（人B）
用途: 提供目标检测/场景理解的统一入口，供 Navigation Agent 和 Perception Agent 调用。

通过阿里云 Qwen-VL 视觉 API 实现，不加载本地模型。
骨架阶段只定义接口签名，不接真实 API。
"""

from __future__ import annotations


async def detect(image_bytes: bytes) -> list[dict]:
    """对输入图像执行视觉检测/场景理解。

    Args:
        image_bytes: 原始图像字节数据

    Returns:
        检测结果列表，每项包含 label, confidence, bbox 等字段。
        骨架阶段返回空列表。

    TODO: Navigation 负责人接入 DashScope Qwen-VL 视觉 API 实现。
    """
    # 占位实现
    return []

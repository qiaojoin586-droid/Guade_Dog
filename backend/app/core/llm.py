"""LLM 客户端封装（占位实现）。

只定义接口签名，骨架阶段不接真实 API。
模型名从 config.py 读取，不硬编码。
支持阿里云 Qwen (DashScope) 和 DeepSeek，通过 httpx 直接调用。
"""

from __future__ import annotations

from app.config import get_settings


async def complete(
    prompt: str,
    model: str | None = None,
    json_mode: bool = False,
) -> str:
    """调用 LLM 生成文本。

    Args:
        prompt: 输入提示词
        model: 模型名称，默认使用配置中的 DASHSCOPE_MODEL
        json_mode: 是否要求 JSON 格式输出

    Returns:
        LLM 生成的文本

    Raises:
        NotImplementedError: 骨架阶段未接入真实 API
    """
    # TODO: 接入真实 LLM API（使用 httpx）
    settings = get_settings()
    _model = model or settings.DASHSCOPE_MODEL
    raise NotImplementedError(
        f"LLM 调用尚未实现 (model={_model}, json_mode={json_mode})"
    )

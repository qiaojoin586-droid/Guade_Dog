"""LLM 客户端封装。

按配置 LLM_PROVIDER 选择供应商:
  * dashscope(默认) —— 阿里千问,OpenAI 兼容 HTTP 接口;
  * spark           —— 讯飞星火 Ultra-32K,WebSocket wss://spark-api.xf-yun.com/v4.0/chat,
                       凭据与 ASR/TTS 共用 XFYUN_* (同一讯飞应用的 APPID/APIKey/APISecret)。

json_mode: Spark 用系统提示词约束 JSON 输出(chat.py 做容错解析);
          DashScope 额外用 response_format=json_object。
"""

from __future__ import annotations

import asyncio
import json
import logging

import httpx
import websockets
from websockets.asyncio.client import connect

from app.config import get_settings
from app.utils.xfyun import build_auth_header, split_ws_url

logger = logging.getLogger(__name__)

DASHSCOPE_COMPAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DEFAULT_TIMEOUT = 40.0
_SPARK_MAX_WS_MESSAGE = 5_000_000
_SPARK_RECV_TIMEOUT = 30.0


class LLMError(Exception):
    """LLM 调用失败(未配置密钥、网络、鉴权、响应异常)。"""


async def complete(
    prompt: str,
    model: str | None = None,
    json_mode: bool = False,
    system: str | None = None,
    temperature: float = 0.2,
) -> str:
    """调用 LLM 生成文本(按 LLM_PROVIDER 分发)。

    Args:
        prompt: 用户输入(语音识别文本)
        model: 模型名称(dashscope 供应商时生效;spark 由 SPARK_DOMAIN 决定)
        json_mode: True 时要求 JSON 格式输出
        system: 可选的系统提示词
        temperature: 采样温度,json_mode 下建议保持低值保证稳定输出

    Returns:
        LLM 返回的文本内容(已 strip)

    Raises:
        LLMError: 任何调用/解析失败,调用方负责兜底。
    """
    provider = get_settings().LLM_PROVIDER.strip().lower()
    if provider in ("spark", "xfyun", "xinghuo"):
        return await _complete_spark(prompt, json_mode=json_mode, system=system, temperature=temperature)
    if provider in ("dashscope", "qwen", "aliyun"):
        return await _complete_dashscope(prompt, model=model, json_mode=json_mode, system=system, temperature=temperature)
    raise LLMError(f"未知 LLM_PROVIDER: {provider}(可选 spark / dashscope)")


# ============================================================
# 供应商: 讯飞星火 (Spark Ultra-32K, WebSocket)
# ============================================================


async def _complete_spark(
    prompt: str,
    json_mode: bool = False,
    system: str | None = None,
    temperature: float = 0.2,
) -> str:
    """调用讯飞星火 v4.0/chat,返回完整回复文本。

    与 ASR/TTS 同一套 HMAC 签名(utils/xfyun.py),凭据取 XFYUN_*。
    消息角色支持 user/assistant/system(星火 v4.0 支持 system)。
    """
    settings = get_settings()
    app_id, api_key, api_secret = (
        settings.XFYUN_APP_ID,
        settings.XFYUN_API_KEY,
        settings.XFYUN_API_SECRET,
    )
    if not (app_id and api_key and api_secret):
        raise LLMError("XFYUN_* 未配置完整,无法调用讯飞星火")

    url = settings.SPARK_CHAT_URL
    host, path = split_ws_url(url)
    auth, date = build_auth_header(host, path, api_key, api_secret)

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "header": {"app_id": app_id, "uid": "guide-dog-ai"},
        "parameter": {
            "chat": {
                "domain": settings.SPARK_DOMAIN,
                "temperature": temperature,
                "max_tokens": 2048,
                "top_k": 5,
            }
        },
        "payload": {"message": {"text": messages}},
    }

    parts: list[str] = []
    timeout = max(settings.SPARK_TIMEOUT_SECONDS, _SPARK_RECV_TIMEOUT)
    try:
        async with connect(
            url,
            additional_headers={"Authorization": auth, "Host": host, "Date": date},
            max_size=_SPARK_MAX_WS_MESSAGE,
            open_timeout=10,
        ) as ws:
            await ws.send(json.dumps(payload))
            while True:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
                header = msg.get("header") or {}
                if header.get("code") != 0:
                    raise LLMError(
                        f"讯飞星火返回错误 code={header.get('code')} msg={header.get('message')}"
                    )
                for choice in ((msg.get("payload") or {}).get("choices") or {}).get("text") or []:
                    parts.append(choice.get("content", ""))
                if header.get("status") == 2:
                    break
    except LLMError:
        raise
    except asyncio.TimeoutError as exc:
        raise LLMError("讯飞星火连接/响应超时") from exc
    except websockets.exceptions.WebSocketException as exc:
        raise LLMError(f"讯飞星火 WebSocket 失败: {exc}") from exc
    except OSError as exc:
        raise LLMError(f"讯飞星火网络错误: {exc}") from exc

    content = "".join(parts).strip()
    if not content:
        raise LLMError("讯飞星火返回空内容")
    return content


# ============================================================
# 供应商: 阿里千问 (DashScope, OpenAI 兼容 HTTP)
# ============================================================


async def _complete_dashscope(
    prompt: str,
    model: str | None = None,
    json_mode: bool = False,
    system: str | None = None,
    temperature: float = 0.2,
) -> str:
    settings = get_settings()
    api_key = settings.DASHSCOPE_API_KEY
    if not api_key:
        raise LLMError("DASHSCOPE_API_KEY 未配置")

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload: dict = {
        "model": model or settings.DASHSCOPE_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(DASHSCOPE_COMPAT_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        if not content:
            raise LLMError("LLM 返回空内容")
        return content
    except httpx.HTTPError as exc:
        logger.warning("LLM 请求失败: %s", exc)
        raise LLMError(f"LLM 请求失败: {exc}") from exc
    except (KeyError, IndexError, ValueError) as exc:
        logger.warning("LLM 响应解析失败: %s", exc)
        raise LLMError(f"LLM 响应解析失败: {exc}") from exc

"""讯飞语音合成(tts) TTS 客户端。

WebSocket 一次请求返回整段音频(base64 分片),拼接后返回 mp3 字节。
参考: https://www.xfyun.cn/doc/tts/online_tts/API.html
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging

import websockets
from websockets.asyncio.client import connect

from app.config import get_settings
from app.utils.xfyun import XfyunError, build_auth_header, split_ws_url

logger = logging.getLogger(__name__)

# 讯飞 TTS 单次请求文本上限(字节),超长截断
MAX_TEXT_BYTES = 4096
# 服务端单条结果帧上限(音频分片可能较大)
MAX_WS_MESSAGE = 5_000_000
_RECV_TIMEOUT = 15.0


def _truncate_utf8(text: str, max_bytes: int = MAX_TEXT_BYTES) -> bytes:
    """按字节截断 UTF-8 文本，且不切断多字节字符。

    直接按字节切分可能把中文等多字节字符切坏，导致讯飞解码失败；
    errors="ignore" 会丢弃截断处的残缺字节，保证结果始终是合法 UTF-8。
    """
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return encoded
    return encoded[:max_bytes].decode("utf-8", errors="ignore").encode("utf-8")


async def tts_synthesize(text: str) -> bytes:
    """将文本合成为 mp3 音频字节。

    Raises:
        XfyunError: 凭据缺失、业务错误码、超时等。
    """
    settings = get_settings()
    app_id, api_key, api_secret = (
        settings.XFYUN_APP_ID,
        settings.XFYUN_API_KEY,
        settings.XFYUN_API_SECRET,
    )
    if not (app_id and api_key and api_secret):
        raise XfyunError("XFYUN_APP_ID / XFYUN_API_KEY / XFYUN_API_SECRET 未配置完整")

    encoded = text.encode("utf-8")
    if len(encoded) > MAX_TEXT_BYTES:
        logger.warning("TTS 文本超长(%d字节),已截断至 %d 字节", len(encoded), MAX_TEXT_BYTES)
        encoded = _truncate_utf8(text)

    host, path = split_ws_url(settings.SPEECH_TTS_URL)
    auth, date = build_auth_header(host, path, api_key, api_secret)

    payload = {
        "common": {"app_id": app_id},
        "business": {
            "aue": "lame",                      # 输出 mp3
            "auf": "audio/L16;rate=16000",
            "vcn": "xiaoyan",                   # 中文女声
            "tte": "UTF8",
            "speed": 50,
            "volume": 50,
            "pitch": 50,
        },
        "data": {"status": 2, "text": base64.b64encode(encoded).decode()},
    }

    chunks: list[bytes] = []
    timeout = max(settings.SPEECH_TTS_TIMEOUT_SECONDS, _RECV_TIMEOUT)

    try:
        async with connect(
            settings.SPEECH_TTS_URL,
            additional_headers={"Authorization": auth, "Host": host, "Date": date},
            max_size=MAX_WS_MESSAGE,
            open_timeout=10,
        ) as ws:
            await ws.send(json.dumps(payload))
            while True:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
                if msg.get("code") != 0:
                    raise XfyunError(
                        f"讯飞 TTS 返回错误 code={msg.get('code')} msg={msg.get('message')}"
                    )
                data = msg.get("data") or {}
                audio_b64 = data.get("audio")
                if audio_b64:
                    chunks.append(base64.b64decode(audio_b64))
                if data.get("status") == 2:
                    break
    except XfyunError:
        raise
    except asyncio.TimeoutError as exc:
        raise XfyunError("讯飞 TTS 连接/响应超时") from exc
    except websockets.exceptions.WebSocketException as exc:
        raise XfyunError(f"讯飞 TTS WebSocket 失败: {exc}") from exc
    except OSError as exc:
        raise XfyunError(f"讯飞 TTS 网络错误: {exc}") from exc

    return b"".join(chunks)

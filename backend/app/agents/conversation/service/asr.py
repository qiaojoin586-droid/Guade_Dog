"""讯飞语音听写(iat) ASR 客户端。

流式 WebSocket 调用: HMAC 签名 → 按 160ms/帧 分帧发送 PCM → 拼接识别结果。
参考: https://www.xfyun.cn/doc/asr/voicedictation/API.html
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

# 16kHz 16bit 单声道: 每帧 160ms = 16000 * 2 * 0.16 = 5120 字节
FRAME_BYTES = 16000 * 2 * 160 // 1000
# 服务端单条结果帧上限(默认 1MB 可能不够,放大到 2MB)
MAX_WS_MESSAGE = 2_000_000
# 单条消息接收超时(秒)
_RECV_TIMEOUT = 15.0


def _split_frames(pcm: bytes) -> tuple[bytes, list[bytes]]:
    """按 160ms/帧切分 PCM,返回 (首帧数据, 中间帧列表)。"""
    chunks = [pcm[i : i + FRAME_BYTES] for i in range(0, len(pcm), FRAME_BYTES)]
    first = chunks[0] if chunks else b""
    return first, chunks[1:]


def _first_frame(app_id: str, sample_rate: int, audio_b64: str) -> str:
    return json.dumps(
        {
            "common": {"app_id": app_id},
            "business": {
                "language": "zh_cn",
                "domain": "iat",
                "accent": "mandarin",
                "vad_eos": 5000,
            },
            "data": {
                "status": 0,
                "format": f"audio/L16;rate={sample_rate}",
                "encoding": "raw",
                "audio": audio_b64,
            },
        }
    )


def _mid_frame(audio_b64: str) -> str:
    return json.dumps({"data": {"status": 1, "audio": audio_b64}})


def _last_frame() -> str:
    return json.dumps({"data": {"status": 2, "audio": ""}})


def _extract_result(msg: dict, texts: list[str], scores: list[float]) -> None:
    """从结果帧中提取增量文本与单字置信度。"""
    result = (msg.get("data") or {}).get("result") or {}
    for seg in result.get("ws") or []:
        for cw in seg.get("cw") or []:
            texts.append(cw.get("w", ""))
            sc = cw.get("sc")
            if sc is not None:
                scores.append(float(sc))


async def asr_from_pcm(pcm: bytes) -> tuple[str, float]:
    """调用讯飞 iat 识别 PCM 音频。

    Returns:
        (识别文本, 平均置信度 0~1;文本为空时置信度为 0.0)

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

    url = settings.SPEECH_ASR_URL
    host, path = split_ws_url(url)
    auth, date = build_auth_header(host, path, api_key, api_secret)

    first, mids = _split_frames(pcm)
    texts: list[str] = []
    scores: list[float] = []
    timeout = max(settings.SPEECH_ASR_TIMEOUT_SECONDS, _RECV_TIMEOUT)

    try:
        async with connect(
            url,
            additional_headers={"Authorization": auth, "Host": host, "Date": date},
            max_size=MAX_WS_MESSAGE,
            open_timeout=10,
        ) as ws:
            # 1) 发首帧(带参数) → 2) 发中间帧 → 3) 发尾帧,然后收结果
            await ws.send(
                _first_frame(app_id, settings.SPEECH_SAMPLE_RATE, base64.b64encode(first).decode())
            )
            for chunk in mids:
                await ws.send(_mid_frame(base64.b64encode(chunk).decode()))
            await ws.send(_last_frame())

            while True:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
                if msg.get("code") != 0:
                    raise XfyunError(
                        f"讯飞 ASR 返回错误 code={msg.get('code')} msg={msg.get('message')}"
                    )
                _extract_result(msg, texts, scores)
                if (msg.get("data") or {}).get("status") == 2:
                    break
    except XfyunError:
        raise
    except asyncio.TimeoutError as exc:
        raise XfyunError("讯飞 ASR 连接/响应超时") from exc
    except websockets.exceptions.WebSocketException as exc:
        raise XfyunError(f"讯飞 ASR WebSocket 失败: {exc}") from exc
    except OSError as exc:
        raise XfyunError(f"讯飞 ASR 网络错误: {exc}") from exc

    text = "".join(texts).strip()
    confidence = round(sum(scores) / len(scores), 4) if scores else 0.0
    return text, confidence

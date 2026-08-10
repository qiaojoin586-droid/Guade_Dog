"""音频处理工具。

通过 ffmpeg 将前端上传的任意音频(webm/wav/mp3 等)转为讯飞 ASR 要求的
PCM16 / 16kHz / 单声道裸流。依赖系统 ffmpeg(需加入 PATH)。
"""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)

FFMPEG_BIN = "ffmpeg"
_TRANSCODE_TIMEOUT = 30


class AudioConvertError(Exception):
    """音频转码失败(无法解码、无有效音频、超时)。"""


def convert_audio_format(audio_bytes: bytes, target_format: str = "pcm16_16k") -> bytes:
    """将音频字节转为指定格式。

    Args:
        audio_bytes: 原始音频字节(webm/wav/mp3 等任意 ffmpeg 可解码格式)
        target_format: pcm16_16k(默认,讯飞要求) | wav

    Returns:
        转换后的音频字节。音频过短/无法解码时抛 AudioConvertError。
    """
    if not audio_bytes or len(audio_bytes) < 100:
        raise AudioConvertError("音频为空或过短")

    if target_format == "pcm16_16k":
        out_args = ["-f", "s16le", "-ar", "16000", "-ac", "1"]
    elif target_format == "wav":
        out_args = ["-f", "wav", "-ar", "16000", "-ac", "1"]
    else:
        raise ValueError(f"不支持的 target_format: {target_format}")

    cmd = [
        FFMPEG_BIN, "-y", "-loglevel", "error", "-nostdin",
        "-i", "pipe:0",
        *out_args,
        "pipe:1",
    ]
    try:
        proc = subprocess.run(cmd, input=audio_bytes, capture_output=True, timeout=_TRANSCODE_TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        raise AudioConvertError("音频转码超时") from exc

    if proc.returncode != 0:
        stderr = (proc.stderr or b"").decode("utf-8", errors="ignore")[:300]
        logger.warning("ffmpeg 转码失败: %s", stderr)
        raise AudioConvertError(f"ffmpeg 转码失败: {stderr}")

    if not proc.stdout:
        raise AudioConvertError("转码结果为空(可能无有效音频)")
    return proc.stdout

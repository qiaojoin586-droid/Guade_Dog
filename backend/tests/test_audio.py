"""音频转码工具测试: 用 ffmpeg 生成正弦波 wav,验证转码为 PCM16/16k 的结果。"""

import subprocess

import pytest

from app.utils.audio import AudioConvertError, convert_audio_format


@pytest.fixture(scope="module")
def sine_wav_bytes() -> bytes:
    """0.5 秒 440Hz 正弦波 wav(ffmpeg 生成)。"""
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-nostdin",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=0.5",
        "-f", "wav", "pipe:1",
    ]
    proc = subprocess.run(cmd, capture_output=True)
    assert proc.returncode == 0, proc.stderr.decode(errors="ignore")
    return proc.stdout


def test_convert_to_pcm16_16k(sine_wav_bytes):
    """0.5s 音频转码后应为 0.5 * 16000 * 2 = 16000 字节。"""
    pcm = convert_audio_format(sine_wav_bytes)
    assert len(pcm) == 16000


def test_convert_empty_audio_raises():
    with pytest.raises(AudioConvertError):
        convert_audio_format(b"")


def test_convert_garbage_raises():
    with pytest.raises(AudioConvertError):
        convert_audio_format(b"\x00" * 500)

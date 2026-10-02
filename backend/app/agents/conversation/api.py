"""Conversation Agent 路由。

路由: /speech/*, /ws/chat, /auth/*, /family/*
归属: 人A（Conversation 负责人）
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.conversation.schemas import ChatRequest, CommandRequest, TTSRequest
from app.agents.conversation.service.asr import asr_from_pcm
from app.agents.conversation.service.chat import chat
from app.agents.conversation.service.commands import handle as handle_command
from app.agents.conversation.service.tts import tts_synthesize
from app.auth.models import User
from app.config import get_settings
from app.core.errors import build_success_response
from app.dependencies import get_current_user, get_db_session
from app.utils.audio import AudioConvertError, convert_audio_format
from app.utils.xfyun import XfyunError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["conversation"])


@router.get("/conversation/ping")
async def ping():
    """Conversation 模块连通性检查。"""
    return build_success_response({"module": "conversation"})


@router.post("/speech/asr", summary="语音识别(讯飞 ASR)")
async def speech_asr(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传音频(webm/wav 等 ffmpeg 可解码格式),返回识别文本。

    - 音频 ≤ SPEECH_MAX_UPLOAD_BYTES(默认 5MB)
    - 识别为空 → 400 提示"没听清,请再说一次"
    """
    settings = get_settings()
    raw = await audio.read()
    if len(raw) < 200:
        raise HTTPException(400, detail="没有听到声音，请再说一次")
    if len(raw) > settings.SPEECH_MAX_UPLOAD_BYTES:
        raise HTTPException(400, detail="音频文件过大，请缩短录音")

    try:
        pcm = convert_audio_format(raw)
    except (AudioConvertError, ValueError) as exc:
        logger.warning("音频转码失败: %s", exc)
        raise HTTPException(400, detail="音频格式无法解析，请重新录音") from exc

    try:
        text, confidence = await asr_from_pcm(pcm)
    except XfyunError as exc:
        logger.error("讯飞 ASR 调用失败: %s", exc)
        raise HTTPException(500, detail="语音识别服务暂不可用，请稍后再试") from exc

    if not text:
        raise HTTPException(400, detail="没听清，请再说一次")
    logger.info("ASR 识别成功 text_len=%d confidence=%s", len(text), confidence)  # 不落原文
    return build_success_response({"text": text, "confidence": confidence})


@router.post("/speech/tts", summary="语音合成(讯飞 TTS)")
async def speech_tts(
    req: TTSRequest,
    current_user: User = Depends(get_current_user),
):
    """将文本合成为 mp3,直接返回音频流(前端 Audio 播放)。"""
    text = req.text.strip()
    if not text:
        raise HTTPException(400, detail="文本不能为空")

    try:
        mp3 = await tts_synthesize(text)
    except XfyunError as exc:
        logger.error("讯飞 TTS 调用失败: %s", exc)
        raise HTTPException(500, detail="语音合成服务暂不可用，请稍后再试") from exc

    if not mp3:
        raise HTTPException(400, detail="语音合成失败，请重试")
    return Response(content=mp3, media_type="audio/mpeg")


@router.post("/conversation/chat", summary="语音对话(LLM + 工具调用)")
async def conversation_chat(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """识别文本进 LLM,判断意图并调用工具。"""
    resp = await chat(
        req.text,
        req.session_id,
        user_id=str(current_user.id),
        coords=req.coords.model_dump() if req.coords else None,
    )
    resp_data = resp.data or {}
    payload: dict = {
        "text": resp.text,
        "tool_called": resp_data.get("tool_called"),
    }
    # 工具结构化结果与动作标识一并上送前端(定位精度/SOS 触发等)
    if resp_data.get("tool_data"):
        payload["tool_data"] = resp_data["tool_data"]
    if resp_data.get("action"):
        payload["action"] = resp_data["action"]
    return build_success_response(payload)


@router.post("/conversation/command", summary="语音指令(演示版规则大脑)")
async def conversation_command(
    req: CommandRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """语音指令总入口：导航、常用地址、拍照识别、紧急求救。

    演示阶段回复全部写死，只有地址簿是真实读写 MySQL；
    action 字段告诉前端要打开哪个画面（摄像头模拟 / 求救确认）。
    """
    result = await handle_command(req.text, current_user.id, db, req.trigger)

    # 规则未命中 → 交给 LLM + 工具链（天气/定位/距离/提醒/闲聊）
    if result.action == "fallback":
        llm_resp = await chat(
            req.text,
            req.session_id,
            user_id=str(current_user.id),
            coords=req.coords.model_dump() if req.coords else None,
        )
        llm_data = llm_resp.data or {}
        return build_success_response(
            {
                "text": llm_resp.text,
                "action": "chat",
                "tool_called": llm_data.get("tool_called"),
                "tool_data": llm_data.get("tool_data") or None,
            }
        )

    return build_success_response(
        {
            "text": result.text,
            "action": result.action,
            "tool_called": result.tool,
            "tool_data": result.data or None,
        }
    )

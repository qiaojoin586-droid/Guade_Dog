"""Safety Agent 路由。

路由: /safety/*
本期能力: 药品识别(medicine) / 健康问答(health) / 钞票识别(currency)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from app.core.errors import (
    ERR_EXT_UNAVAILABLE,
    ERR_INTERNAL,
    ERR_INVALID_INPUT,
    build_error_response,
    build_success_response,
)
from app.utils.image import MAX_UPLOAD_BYTES, ImageValidationError

from .schemas import HealthAsk
from .service import currency, health, medicine
from .service.vision import VisionError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["safety"])


@router.get("/safety/ping")
async def ping():
    """Safety 模块连通性检查。"""
    return build_success_response({"module": "safety"})


@router.post("/safety/medicine/recognize")
async def recognize_medicine(image: UploadFile = File(...)):
    """药品识别：上传药盒/药瓶照片，返回药品信息与播报文案。"""
    return await _handle_image_upload(image, medicine.recognize)


@router.post("/safety/currency/recognize")
async def recognize_currency(image: UploadFile = File(...)):
    """钞票识别：上传纸币照片，返回面额与播报文案。"""
    return await _handle_image_upload(image, currency.recognize)


@router.post("/safety/health/ask")
async def ask_health(req: HealthAsk):
    """健康问答：返回回答与播报文案（带安全护栏）。"""
    try:
        result = await health.ask(req.question)
        return build_success_response(result)
    except Exception as exc:  # LLM 等失败统一兜底
        logger.warning("健康问答失败: %s", exc)
        return JSONResponse(
            status_code=503,
            content=build_error_response(
                code=ERR_EXT_UNAVAILABLE,
                message="网络繁忙，请稍后再试",
            ),
        )


async def _handle_image_upload(image: UploadFile, handler) -> JSONResponse:
    """图片识别通用处理：读取 → 校验大小 → 调用识别服务 → 统一响应/错误。"""
    # 预检：优先按 Content-Length 拦截超限上传，避免整读进内存
    if image.size is not None and image.size > MAX_UPLOAD_BYTES:
        return JSONResponse(
            status_code=400,
            content=build_error_response(code=ERR_INVALID_INPUT, message="图片不能超过 10MB"),
        )
    try:
        image_bytes = await image.read()
    except Exception as exc:
        logger.warning("读取上传图片失败: %s", exc)
        return JSONResponse(
            status_code=400,
            content=build_error_response(code=ERR_INVALID_INPUT, message="请拍摄药盒或钞票的照片"),
        )

    if len(image_bytes) > MAX_UPLOAD_BYTES:
        return JSONResponse(
            status_code=400,
            content=build_error_response(code=ERR_INVALID_INPUT, message="图片不能超过 10MB"),
        )

    try:
        result = await handler(image_bytes)
        return build_success_response(result)
    except VisionError as exc:
        logger.warning("识别失败 code=%s detail=%s", exc.code, exc.detail or exc.message)
        status = 400 if exc.code == ERR_INVALID_INPUT else 422 if exc.code == 40200 else 503
        return JSONResponse(
            status_code=status,
            content=build_error_response(code=exc.code, message=exc.fallback_text),
        )
    except ImageValidationError as exc:
        return JSONResponse(
            status_code=400,
            content=build_error_response(code=ERR_INVALID_INPUT, message=str(exc)),
        )
    except Exception as exc:
        logger.exception("识别接口异常: %s", exc)
        return JSONResponse(
            status_code=500,
            content=build_error_response(code=ERR_INTERNAL, message="系统繁忙，请稍后重试"),
        )
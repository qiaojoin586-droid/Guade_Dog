"""导盲AI智能体 FastAPI 应用工厂。

职责：
- 创建 FastAPI 实例并配置 CORS
- 挂载 4 个 Agent 模块路由（每模块一行）
- 注册中间件（request_id）、统一异常处理
- 提供 GET /health 端点
"""

from __future__ import annotations


import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.errors import ERR_INTERNAL, build_error_response

# uvicorn 默认不配置 root logger,应用日志(如工具调用占位)不会输出;
# basicConfig 仅在 root 无 handler 时生效,不影响 uvicorn 自身日志。
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    settings = get_settings()
    logger.info("启动导盲AI智能体后端 [%s] debug=%s", settings.APP_NAME, settings.DEBUG)
    yield
    logger.info("关闭导盲AI智能体后端")


def create_app() -> FastAPI:
    """应用工厂函数，供 uvicorn 与测试复用。"""
    settings = get_settings()

    app = FastAPI(
        title="导盲AI智能体",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── request_id 中间件 ──
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # ── 统一异常处理 ──
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = request.headers.get("X-Request-ID", "")
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_response(
                code=exc.status_code * 100 + 1,  # 映射到错误码体系
                message=exc.detail if isinstance(exc.detail, str) else str(exc.detail),
                request_id=request_id,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = request.headers.get("X-Request-ID", "")
        return JSONResponse(
            status_code=422,
            content=build_error_response(
                code=40001,
                message="参数校验失败",
                detail=str(exc.errors()),
                request_id=request_id,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = request.headers.get("X-Request-ID", "")
        logger.exception("未捕获异常: %s", exc)
        return JSONResponse(
            status_code=500,
            content=build_error_response(
                code=ERR_INTERNAL,
                message="系统繁忙，请稍后重试",
                request_id=request_id,
            ),
        )

    # ── 健康检查 ──
    @app.get("/health", tags=["system"])
    async def health_check():
        return {"status": "ok"}

    # ── 挂载认证路由 ──
    from app.auth.api import router as auth_router

    app.include_router(auth_router)

    # ── 挂载用户资料路由 ──
    from app.users.api import router as users_router

    app.include_router(users_router)

    # ── 挂载 4 个 Agent 模块路由（每模块一行，集成点） ──
    from app.agents.conversation.api import router as conversation_router
    from app.agents.navigation.api import router as navigation_router
    from app.agents.safety.api import router as safety_router
    from app.agents.perception.api import router as perception_router

    app.include_router(conversation_router)
    app.include_router(navigation_router)
    app.include_router(safety_router)
    app.include_router(perception_router)

    return app

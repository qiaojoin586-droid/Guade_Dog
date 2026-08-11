"""配置加载枢纽。

配置来源（优先级从高到低）：
1. 环境变量 —— 系统环境变量 > backend/.env（敏感配置只允许放这里）
2. backend/config.yaml —— 非敏感、结构化配置
3. 内置占位默认值 —— 仅兜底，避免缺配置直接崩

安全约定：SECRET_KEY、密码、API key 等敏感字段只从环境变量读取，
禁止写入 config.yaml 或代码中。

所有代码通过 get_settings() 访问配置，字段名与 .env 键一一对应。
"""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, fields
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

# backend/ 目录（无论从哪个 CWD 启动都能找到配置文件）
BASE_DIR = Path(__file__).resolve().parent.parent

# 加载 backend/.env；override=False 保证系统环境变量优先
load_dotenv(BASE_DIR / ".env", override=False)

# ============================================================
# config.yaml 键 → Settings 字段名 映射
# ============================================================
_YAML_MAP: dict[str, dict[str, str]] = {
    "app": {
        "name": "APP_NAME",
        "debug": "DEBUG",
        "api_v1_prefix": "API_V1_PREFIX",
    },
    "database": {
        "host": "MYSQL_HOST",
        "port": "MYSQL_PORT",
        "db": "MYSQL_DB",
        "charset": "MYSQL_CHARSET",
    },
    "minio": {
        "endpoint": "MINIO_ENDPOINT",
        "bucket": "MINIO_BUCKET",
    },
    "models": {
        "provider": "LLM_PROVIDER",
        "dashscope": "DASHSCOPE_MODEL",
        "dashscope_vision": "DASHSCOPE_VISION_MODEL",
        "spark_url": "SPARK_CHAT_URL",
        "spark_domain": "SPARK_DOMAIN",
        "spark_timeout_seconds": "SPARK_TIMEOUT_SECONDS",
    },
    "speech": {
        "asr_url": "SPEECH_ASR_URL",
        "tts_url": "SPEECH_TTS_URL",
        "sample_rate": "SPEECH_SAMPLE_RATE",
        "asr_timeout_seconds": "SPEECH_ASR_TIMEOUT_SECONDS",
        "tts_timeout_seconds": "SPEECH_TTS_TIMEOUT_SECONDS",
        "max_upload_bytes": "SPEECH_MAX_UPLOAD_BYTES",
    },
    "jwt": {
        "algorithm": "JWT_ALGORITHM",
        "access_expire_minutes": "JWT_ACCESS_EXPIRE_MINUTES",
        "refresh_expire_days": "JWT_REFRESH_EXPIRE_DAYS",
    },
    "websocket": {
        "heartbeat_interval": "WS_HEARTBEAT_INTERVAL",
        "reconnect_delay": "WS_RECONNECT_DELAY",
    },
}

# 仅允许通过 .env / 环境变量配置的敏感字段
_ENV_ONLY: set[str] = {
    "SECRET_KEY",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
    "DASHSCOPE_API_KEY",
    "XFYUN_APP_ID",
    "XFYUN_API_KEY",
    "XFYUN_API_SECRET",
    "AMAP_API_KEY",
    "QWEATHER_API_KEY",
    "JWT_SECRET_KEY",
    "CELERY_BROKER_URL",
}

# 视为"未配置"的占位值
_PLACEHOLDERS: set[str] = {
    "",
    "xxx",
    "sk-xxx",
    "change-me",
    "your-secret-key-change-in-production",
}

# 缺失时打印警告的密钥（用途说明）
_WARN_KEYS: list[tuple[str, str]] = [
    ("SECRET_KEY", "全局签名密钥"),
    ("JWT_SECRET_KEY", "JWT 签名密钥"),
    ("DASHSCOPE_API_KEY", "阿里云 Qwen"),
    ("XFYUN_APP_ID", "讯飞语音"),
    ("AMAP_API_KEY", "高德地图"),
    ("QWEATHER_API_KEY", "和风天气"),
]

# ============================================================
# Settings
# ============================================================


@dataclass
class Settings:
    """应用全局配置。字段名 = .env 键名 = config.yaml 映射目标。"""

    # ===== 应用基础 =====
    APP_NAME: str = "guide-dog-ai"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me"
    API_V1_PREFIX: str = "/api/v1"

    # ===== 数据库 (MySQL 8) =====
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = "guide_dog"
    MYSQL_USER: str = "guide_dog_user"
    MYSQL_PASSWORD: str = "change-me"
    MYSQL_CHARSET: str = "utf8mb4"

    # ===== 任务队列 (Phase 2+ 启用) =====
    CELERY_BROKER_URL: Optional[str] = None

    # ===== 对象存储 (MinIO) =====
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "guide-dog-assets"

    # ===== LLM 供应商选择 =====
    # provider: dashscope(阿里千问,默认) | spark(讯飞星火备用)
    LLM_PROVIDER: str = "dashscope"
    # 讯飞星火 (WebSocket, 与 ASR/TTS 共用 XFYUN_* 凭据)
    SPARK_CHAT_URL: str = "wss://spark-api.xf-yun.com/v4.0/chat"
    SPARK_DOMAIN: str = "4.0Ultra"        # Spark Ultra-32K
    SPARK_TIMEOUT_SECONDS: float = 30.0

    # ===== 阿里云 Qwen (DashScope) — 备用 LLM 与多模态 =====
    DASHSCOPE_API_KEY: Optional[str] = None
    DASHSCOPE_MODEL: str = "qwen-max"          # 核心调度 LLM（意图判断/对话）
    DASHSCOPE_VISION_MODEL: str = "qwen-vl-max"  # 多模态（图像理解）

    # ===== 讯飞语音（ASR 语音转文字） =====
    XFYUN_APP_ID: Optional[str] = None
    XFYUN_API_KEY: Optional[str] = None
    XFYUN_API_SECRET: Optional[str] = None

    # ===== 语音 (讯飞 ASR/TTS) =====
    # 凭据 XFYUN_* 在 .env;以下为非敏感运行参数
    SPEECH_ASR_URL: str = "wss://iat-api.xfyun.cn/v2/iat"
    SPEECH_TTS_URL: str = "wss://tts-api.xfyun.cn/v2/tts"
    SPEECH_SAMPLE_RATE: int = 16000
    SPEECH_ASR_TIMEOUT_SECONDS: float = 15.0
    SPEECH_TTS_TIMEOUT_SECONDS: float = 15.0
    SPEECH_MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024

    # ===== 高德地图 / 和风天气 =====
    AMAP_API_KEY: Optional[str] = None
    QWEATHER_API_KEY: Optional[str] = None

    # ===== JWT =====
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_EXPIRE_DAYS: int = 7

    # ===== WebSocket =====
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_RECONNECT_DELAY: int = 3

    @property
    def database_url(self) -> str:
        """SQLAlchemy async 连接串。"""
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
            f"?charset={self.MYSQL_CHARSET}"
        )

    @property
    def database_url_sync(self) -> str:
        """同步连接串（Alembic 用）。"""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"
            f"?charset={self.MYSQL_CHARSET}"
        )


# ============================================================
# 加载逻辑
# ============================================================


def _coerce(value: Any, default: Any) -> Any:
    """环境变量是字符串，按默认值类型做转换。"""
    if isinstance(default, bool):
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("1", "true", "yes", "on")
    if isinstance(default, int):
        return int(value)
    return value


@lru_cache
def _yaml_flat() -> dict[str, Any]:
    """读取 config/config.yaml 并展平为 {Settings字段名: 值}。"""
    path = BASE_DIR / "config" / "config.yaml"
    if not path.exists():
        warnings.warn(f"未找到配置文件 {path}，仅使用 .env 与环境变量", stacklevel=2)
        return {}
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    flat: dict[str, Any] = {}
    for section, fields_map in _YAML_MAP.items():
        section_data = raw.get(section) or {}
        for yaml_key, field_name in fields_map.items():
            if yaml_key in section_data and section_data[yaml_key] is not None:
                flat[field_name] = section_data[yaml_key]
    return flat


def _is_unset(value: Any) -> bool:
    """判断值是否缺失或为占位值。"""
    return value is None or str(value).strip() in _PLACEHOLDERS


def _build_settings() -> Settings:
    """按优先级（env > yaml > 默认值）组装 Settings。"""
    yaml_flat = _yaml_flat()
    kwargs: dict[str, Any] = {}
    for f in fields(Settings):
        name = f.name
        default = f.default  # dataclass 默认值（兜底）

        # 1) 环境变量（系统 > .env，load_dotenv 已按此顺序填充）
        env_value = os.getenv(name)
        if not _is_unset(env_value):
            kwargs[name] = _coerce(env_value, default)
            continue

        # 2) config.yaml（敏感字段不会出现在 yaml 中）
        if name in yaml_flat and not _is_unset(yaml_flat[name]):
            kwargs[name] = yaml_flat[name]
            continue

        # 3) 内置默认值兜底
        kwargs[name] = default

    return Settings(**kwargs)


def get_settings() -> Settings:
    """获取全局配置单例。"""
    global _settings
    if _settings is None:
        _settings = _build_settings()
        _warn_missing_keys(_settings)
    return _settings


def _warn_missing_keys(settings: Settings) -> None:
    """启动时检查敏感密钥，缺失/占位则打印警告。"""
    missing = [f"{key}({label})" for key, label in _WARN_KEYS if _is_unset(getattr(settings, key))]
    if missing:
        warnings.warn(
            f"以下密钥未配置（请在 backend/.env 中设置），相关功能将不可用: {', '.join(missing)}",
            stacklevel=2,
        )
    # 讯飞 APIKey 与 APISecret 是两个不同的随机串,填成一样必然验签失败
    if (
        settings.XFYUN_API_KEY
        and settings.XFYUN_API_SECRET
        and settings.XFYUN_API_KEY == settings.XFYUN_API_SECRET
    ):
        warnings.warn(
            "XFYUN_API_KEY 与 XFYUN_API_SECRET 相同!请到讯飞控制台「我的应用」分别复制 "
            "APIKey 与 APISecret 两个字段,它们必须是不同的字符串",
            stacklevel=2,
        )


# 全局单例
_settings: Settings | None = None

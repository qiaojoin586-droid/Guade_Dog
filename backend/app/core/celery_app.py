"""Celery 配置（Phase 2+ 占位）。

骨架阶段不启动 Celery worker，仅预留实例定义。
broker 将使用 MySQL（CELERY_BROKER_URL 在 .env 中配置）。
"""

from __future__ import annotations

# TODO: Phase 2+ 启用时取消注释
# from celery import Celery
# from app.config import get_settings
#
# settings = get_settings()
# celery_app = Celery(
#     "guide_dog",
#     broker=settings.CELERY_BROKER_URL,
#     include=["app.agents.*.tasks"],
# )
# celery_app.conf.update(
#     task_serializer="json",
#     accept_content=["json"],
#     result_serializer="json",
#     timezone="Asia/Shanghai",
#     enable_utc=True,
# )

# 占位：避免 import 报错
celery_app = None

"""数据库连接与 ORM 基础对象。

SQLAlchemy 2.0 async + aiomysql（MySQL 8）。
导出 Base（所有模块 models.py 继承）与 engine。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """所有模型继承此基类。"""
    pass


_settings = get_settings()

engine: AsyncEngine = create_async_engine(
    _settings.database_url,
    echo=_settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncSession:
    """获取异步数据库会话（上下文管理器）。"""
    async with async_session_factory() as session:
        yield session

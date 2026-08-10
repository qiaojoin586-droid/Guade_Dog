"""User SQLAlchemy 模型。

与 init_db.sql 的 users 表结构一致。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    """用户表。"""

    __tablename__ = "users"

    # SQLite（测试环境）仅对 INTEGER PRIMARY KEY 自增，MySQL 用 BIGINT
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="手机号")
    email: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True, comment="邮箱")
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False, comment="密码哈希")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="姓名")
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="blind", comment="角色")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", comment="状态")
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="头像URL")
    medical_notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="健康备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

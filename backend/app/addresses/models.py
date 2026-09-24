"""常用地址 SQLAlchemy 模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserAddress(Base):
    """用户常用地址表（别名 + 详细地址）。

    一个用户下别名唯一，例如“家”“公司”“健身房”。
    """

    __tablename__ = "user_addresses"
    __table_args__ = (
        UniqueConstraint("user_id", "label", name="uq_user_addresses_label"),
        Index("ix_user_addresses_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="用户ID")
    label: Mapped[str] = mapped_column(String(20), nullable=False, comment="别名: 家/公司/健身房")
    address: Mapped[str] = mapped_column(String(255), nullable=False, comment="详细地址")
    lat: Mapped[float | None] = mapped_column(Float, nullable=True, comment="纬度")
    lng: Mapped[float | None] = mapped_column(Float, nullable=True, comment="经度")
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="是否默认地址"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

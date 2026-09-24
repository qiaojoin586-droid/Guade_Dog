"""常用地址业务逻辑。"""

from __future__ import annotations

import logging
import re
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.addresses.models import UserAddress
from app.addresses.schemas import AddressCreate, AddressUpdate

logger = logging.getLogger(__name__)

# 语音里的口语修饰词，匹配别名前先去掉
_NOISE = ("我的", "我", "的地址", "地址", "那个", "一下")


def _clean(text: str) -> str:
    """去掉空格、标点与口语修饰词，便于别名匹配。"""
    cleaned = re.sub(r"[\s，,。.！!？?、：:；;\"'“”‘’]", "", text.strip())
    for word in _NOISE:
        cleaned = cleaned.replace(word, "")
    return cleaned


async def list_addresses(db: AsyncSession, user_id: int) -> Sequence[UserAddress]:
    """按创建顺序返回用户的全部常用地址。"""
    stmt = (
        select(UserAddress)
        .where(UserAddress.user_id == user_id)
        .order_by(UserAddress.created_at.asc(), UserAddress.id.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_address(db: AsyncSession, user_id: int, address_id: int) -> UserAddress | None:
    """按主键取某个用户的地址（他人地址不可见）。"""
    stmt = select(UserAddress).where(
        UserAddress.id == address_id, UserAddress.user_id == user_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def find_by_alias(db: AsyncSession, user_id: int, alias: str) -> UserAddress | None:
    """按别名做宽松匹配：精确 > 别名包含 > 地址包含。

    用于“我要去公司”这类指令；找不到返回 None，由调用方决定是否按字面目的地处理。
    """
    target = _clean(alias)
    if not target:
        return None

    addresses = await list_addresses(db, user_id)
    if not addresses:
        return None

    for item in addresses:
        if _clean(item.label) == target:
            return item

    for item in addresses:
        label = _clean(item.label)
        if label and (label in target or target in label):
            return item

    for item in addresses:
        if target in item.address:
            return item

    return None


async def find_home(db: AsyncSession, user_id: int) -> UserAddress | None:
    """取“家”地址：优先别名包含“家”，其次默认地址。"""
    addresses = await list_addresses(db, user_id)
    for item in addresses:
        if "家" in item.label:
            return item
    for item in addresses:
        if item.is_default:
            return item
    return None


async def create_address(
    db: AsyncSession, user_id: int, data: AddressCreate
) -> UserAddress:
    """新增地址；同用户下别名不允许重复。

    Raises:
        ValueError: 别名已存在
    """
    existing = await find_by_alias_exact(db, user_id, data.label)
    if existing is not None:
        raise ValueError(f"您已经保存过“{existing.label}”这个地址了，可以说“把{existing.label}地址改成新地址”")

    if data.is_default:
        await _clear_default(db, user_id)

    item = UserAddress(
        user_id=user_id,
        label=data.label,
        address=data.address,
        lat=data.lat,
        lng=data.lng,
        is_default=data.is_default,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    logger.info("新增常用地址 user_id=%s label=%s", user_id, item.label)
    return item


async def find_by_alias_exact(
    db: AsyncSession, user_id: int, label: str
) -> UserAddress | None:
    """按别名精确查找（用于查重）。"""
    stmt = select(UserAddress).where(
        UserAddress.user_id == user_id, UserAddress.label == label.strip()
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_address(
    db: AsyncSession, user_id: int, address_id: int, data: AddressUpdate
) -> UserAddress:
    """修改地址。

    Raises:
        ValueError: 地址不存在或改后的别名与他人重复
    """
    item = await get_address(db, user_id, address_id)
    if item is None:
        raise ValueError("地址不存在")

    if data.label is not None and data.label != item.label:
        duplicated = await find_by_alias_exact(db, user_id, data.label)
        if duplicated is not None and duplicated.id != item.id:
            raise ValueError(f"别名“{data.label}”已被占用")
        item.label = data.label

    if data.address is not None:
        item.address = data.address
    if data.lat is not None:
        item.lat = data.lat
    if data.lng is not None:
        item.lng = data.lng
    if data.is_default is not None:
        if data.is_default:
            await _clear_default(db, user_id)
        item.is_default = data.is_default

    await db.commit()
    await db.refresh(item)
    logger.info("修改常用地址 user_id=%s address_id=%s", user_id, item.id)
    return item


async def delete_address(db: AsyncSession, user_id: int, address_id: int) -> None:
    """删除地址。

    Raises:
        ValueError: 地址不存在
    """
    item = await get_address(db, user_id, address_id)
    if item is None:
        raise ValueError("地址不存在")
    await db.delete(item)
    await db.commit()
    logger.info("删除常用地址 user_id=%s address_id=%s", user_id, address_id)


async def _clear_default(db: AsyncSession, user_id: int) -> None:
    """清除该用户其它默认地址标记。"""
    addresses = await list_addresses(db, user_id)
    for item in addresses:
        if item.is_default:
            item.is_default = False

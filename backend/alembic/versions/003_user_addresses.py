"""新增 user_addresses 常用地址表。

Revision ID: 003_user_addresses
Revises: 002_phone_unique
Create Date: 2026-10-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_user_addresses"
down_revision: Union[str, None] = "002_phone_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_addresses",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="用户ID"),
        sa.Column("label", sa.String(length=20), nullable=False, comment="别名: 家/公司/健身房"),
        sa.Column("address", sa.String(length=255), nullable=False, comment="详细地址"),
        sa.Column("lat", sa.Float(), nullable=True, comment="纬度"),
        sa.Column("lng", sa.Float(), nullable=True, comment="经度"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="是否默认地址"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "label", name="uq_user_addresses_label"),
    )
    op.create_index("ix_user_addresses_user", "user_addresses", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_addresses_user", table_name="user_addresses")
    op.drop_table("user_addresses")

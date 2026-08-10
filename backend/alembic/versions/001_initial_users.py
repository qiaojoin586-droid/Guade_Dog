"""初始迁移 — 创建 users 表。

Revision ID: 001_initial
Revises:
Create Date: 2026-08-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("phone", sa.String(20), nullable=True, comment="手机号"),
        sa.Column("email", sa.String(120), nullable=True, unique=True, comment="邮箱"),
        sa.Column("password_hash", sa.String(256), nullable=False, comment="密码哈希"),
        sa.Column("name", sa.String(50), nullable=False, comment="姓名"),
        sa.Column("role", sa.String(20), nullable=False, server_default="blind", comment="角色: blind/family/admin"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active", comment="状态: active/disabled"),
        sa.Column("medical_notes", sa.Text(), nullable=True, comment="健康备注"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_phone", "users", ["phone"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_table("users")

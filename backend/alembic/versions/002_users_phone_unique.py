"""users.phone 增加唯一约束。

Revision ID: 002_phone_unique
Revises: 001_initial
Create Date: 2026-08-10
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_phone_unique"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 先清理重复手机号（保留 id 最小的一条），否则唯一索引创建会失败
    op.execute(
        """
        DELETE u1 FROM users u1
        JOIN users u2 ON u1.phone = u2.phone AND u1.id > u2.id
        WHERE u1.phone IS NOT NULL
        """
    )
    op.drop_index("ix_users_phone", table_name="users")
    op.create_index("ix_users_phone", table_name="users", columns=["phone"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_phone", table_name="users")
    op.create_index("ix_users_phone", table_name="users", columns=["phone"], unique=False)

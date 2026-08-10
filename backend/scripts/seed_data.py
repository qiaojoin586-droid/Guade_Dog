"""插入测试用户脚本。

用法:
  cd backend
  python scripts/seed_data.py

在数据库中插入一条测试用户记录:
  手机号: admin
  密码: admin (bcrypt 哈希存储)
  角色: admin
  状态: active
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# 确保能导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt
import pymysql


def hash_password(password: str) -> str:
    """使用 bcrypt 对密码进行哈希。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def seed_test_user() -> None:
    """插入测试用户（如果不存在）。"""
    # 从环境变量或默认值读取数据库配置
    import os
    host = os.getenv("MYSQL_HOST", "localhost")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    db = os.getenv("MYSQL_DB", "guide_dog")
    user = os.getenv("MYSQL_USER", "guide_dog_user")
    password = os.getenv("MYSQL_PASSWORD", "change-me")

    conn = pymysql.connect(
        host=host, port=port, user=user, password=password, database=db, charset="utf8mb4"
    )
    try:
        with conn.cursor() as cursor:
            # 检查是否已存在
            cursor.execute("SELECT id FROM users WHERE phone = %s", ("admin",))
            if cursor.fetchone():
                print("测试用户 admin 已存在，跳过插入")
                return

            password_hash = hash_password("admin")
            cursor.execute(
                """INSERT INTO users (phone, password_hash, name, role, status)
                   VALUES (%s, %s, %s, %s, %s)""",
                ("admin", password_hash, "管理员", "admin", "active"),
            )
            conn.commit()
            print("测试用户插入成功: phone=admin, password=admin, role=admin")
    finally:
        conn.close()


if __name__ == "__main__":
    seed_test_user()

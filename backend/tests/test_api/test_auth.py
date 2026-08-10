"""认证接口测试：注册、登录、Token 刷新。"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_db_session
from app.main import create_app


def make_client(app, db_session):
    app.dependency_overrides[get_db_session] = lambda: db_session
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_register_and_login_flow(db_session):
    """注册（手机号）→ 登录 → 用 access token 访问 /users/me。"""
    app = create_app()
    async with make_client(app, db_session) as client:
        # 注册
        resp = await client.post("/api/v1/auth/register", json={
            "phone": "13800138000",
            "password": "password123",
            "name": "测试用户",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["code"] == 200
        assert body["data"]["role"] == "blind"

        # 重复注册 → 400
        resp = await client.post("/api/v1/auth/register", json={
            "phone": "13800138000",
            "password": "password123",
            "name": "重复用户",
        })
        assert resp.status_code == 400
        assert resp.json()["code"] == 40001

        # 登录
        resp = await client.post("/api/v1/auth/login", json={
            "account": "13800138000",
            "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["phone"] == "13800138000"

        # access token 访问 /users/me
        resp = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["phone"] == "13800138000"


@pytest.mark.asyncio
async def test_register_with_email(db_session):
    """仅邮箱注册 → 用邮箱登录。"""
    app = create_app()
    async with make_client(app, db_session) as client:
        resp = await client.post("/api/v1/auth/register", json={
            "email": "user@example.com",
            "password": "password123",
            "name": "邮箱用户",
        })
        assert resp.status_code == 200

        # 邮箱重复 → 400
        resp = await client.post("/api/v1/auth/register", json={
            "email": "user@example.com",
            "password": "password456",
            "name": "重复邮箱",
        })
        assert resp.status_code == 400

        # 邮箱登录
        resp = await client.post("/api/v1/auth/login", json={
            "account": "user@example.com",
            "password": "password123",
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_register_validation(db_session):
    """注册参数校验：非法手机号/邮箱、缺少身份、role 提权、超长密码。"""
    app = create_app()
    async with make_client(app, db_session) as client:
        # 非法手机号 → 422
        resp = await client.post("/api/v1/auth/register", json={
            "phone": "12345",
            "password": "password123",
            "name": "x",
        })
        assert resp.status_code == 422

        # 非法邮箱 → 422
        resp = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "password123",
            "name": "x",
        })
        assert resp.status_code == 422

        # 手机号邮箱都为空 → 422
        resp = await client.post("/api/v1/auth/register", json={
            "password": "password123",
            "name": "x",
        })
        assert resp.status_code == 422

        # 尝试注册 admin → 422（禁止自提权）
        resp = await client.post("/api/v1/auth/register", json={
            "phone": "13800138001",
            "password": "password123",
            "name": "x",
            "role": "admin",
        })
        assert resp.status_code == 422

        # 超长密码（>72 字节）注册成功且可正常登录（bcrypt 截断）
        long_password = "密" * 100
        resp = await client.post("/api/v1/auth/register", json={
            "phone": "13800138002",
            "password": long_password,
            "name": "长密码",
        })
        assert resp.status_code == 200
        resp = await client.post("/api/v1/auth/login", json={
            "account": "13800138002",
            "password": long_password,
        })
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_login_failures(db_session):
    """登录失败：用户不存在、密码错误 → HTTP 400 + code 40001。"""
    app = create_app()
    async with make_client(app, db_session) as client:
        await client.post("/api/v1/auth/register", json={
            "phone": "13800138000",
            "password": "password123",
            "name": "测试用户",
        })

        resp = await client.post("/api/v1/auth/login", json={
            "account": "13800138000",
            "password": "wrong-password",
        })
        assert resp.status_code == 400
        assert resp.json()["code"] == 40001

        resp = await client.post("/api/v1/auth/login", json={
            "account": "19999999999",
            "password": "password123",
        })
        assert resp.status_code == 400
        assert resp.json()["code"] == 40001


@pytest.mark.asyncio
async def test_refresh_flow(db_session):
    """刷新 token 换取新 access token；过期/无效 refresh token → 401。"""
    app = create_app()
    async with make_client(app, db_session) as client:
        await client.post("/api/v1/auth/register", json={
            "phone": "13800138000",
            "password": "password123",
            "name": "测试用户",
        })
        resp = await client.post("/api/v1/auth/login", json={
            "account": "13800138000",
            "password": "password123",
        })
        tokens = resp.json()["data"]

        # 刷新成功 → 新 access token 可用
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert resp.status_code == 200
        new_tokens = resp.json()["data"]
        assert new_tokens["access_token"]
        assert new_tokens["refresh_token"]

        resp = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
        )
        assert resp.status_code == 200

        # 无效 refresh token → 401
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "garbage.token.here",
        })
        assert resp.status_code == 401

        # access token 不能当 refresh token 用 → 401
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": tokens["access_token"],
        })
        assert resp.status_code == 401

        # refresh token 不能当 access token 访问受保护接口 → 401
        resp = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
        )
        assert resp.status_code == 401

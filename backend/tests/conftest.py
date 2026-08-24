"""pytest 全局 fixtures — 内存数据库 + 假 Redis + 测试客户端。

测试策略（模仿主流 FastAPI 项目的标准做法）：
  1. 数据库：SQLite 内存库（aiosqlite + StaticPool 共享连接），不碰生产 MySQL
  2. Redis：fakeredis 内存假 Redis，不依赖真实 Redis 服务
  3. 客户端：httpx.ASGITransport 直连 FastAPI app，不起 HTTP 服务器
  4. 依赖覆盖：dependency_overrides 把 get_db_session / get_redis 换成测试实现
  5. 隔离：每个测试函数独立建表 + 独立假 Redis，互不影响

种子数据：admin 角色 + admin 用户（admin / admin123），密码哈希用项目自己的 hash_password。
"""

import fakeredis
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import BigInteger, Integer
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core import dependencies
from app.core.security import hash_password
from app.core.storage import Base
from app.main import app
from app.system.models import Role, User


# SQLite 只对 INTEGER PRIMARY KEY 自动自增，而 models 主键用的是 BigInteger（生产 MySQL 的 BIGINT）。
# import 时执行一次，把 BigInteger 列换成「SQLite 下用 Integer」的变体：
# SQLite 建 INTEGER（能自增），MySQL 仍渲染 BIGINT，生产代码完全不受影响。
for _table in Base.metadata.tables.values():
    for _column in _table.columns:
        if isinstance(_column.type, BigInteger):
            _column.type = _column.type.with_variant(Integer, "sqlite")


@pytest_asyncio.fixture
async def db_session_factory():
    """SQLite 内存库 + 建表，返回 Session 工厂。

    测试可直接用这个 factory 造数据（比如创建禁用用户、无角色用户）。
    """
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # 让所有连接共享同一个内存库（否则每个连接看到空库）
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _seed_admin(factory):
    """创建 admin 角色 + admin 用户（admin / admin123），返回用户 ID。"""
    async with factory() as session:
        role = Role(code="admin", name="管理员", is_system=True)
        session.add(role)
        await session.flush()  # 拿到 role.id 再挂到 user 上

        user = User(
            username="admin",
            password_hash=await hash_password("admin123"),
            display_name="管理员",
            is_active=True,
        )
        user.roles = [role]
        session.add(user)
        await session.commit()
        return user.id


@pytest_asyncio.fixture
async def client(db_session_factory):
    """测试客户端 — 建表 + 种子 admin + 覆盖依赖（SQLite / fakeredis）。"""
    await _seed_admin(db_session_factory)

    # 数据库会话 → 指向 SQLite 测试库
    async def override_db():
        async with db_session_factory() as session:
            yield session

    # Redis → fakeredis 内存假 Redis
    fake_redis = fakeredis.FakeAsyncRedis(decode_responses=True)

    async def override_redis():
        return fake_redis

    app.dependency_overrides[dependencies.get_db_session] = override_db
    app.dependency_overrides[dependencies.get_redis] = override_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.fake_redis = fake_redis  # 测试里可直接断言 Redis 里的状态
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_headers(client):
    """登录 admin，返回带 Bearer token 的请求头。

    系统管理接口都需要 user:*/role:* 等 scope 权限，admin 角色拥有全部权限（绕过 scope 检查）。
    测试统一用 admin 身份调用，专注测业务逻辑而非权限体系。
    """
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.json()["code"] == 0
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}

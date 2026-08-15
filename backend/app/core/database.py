"""
数据库核心模块 — 异步引擎、连接池、ORM 基类、依赖注入。

FastAPI 的数据库访问模式：
  1. 收到请求 → 从连接池拿一个连接
  2. 创建 Session（一个请求一个 Session，自动开启事务）
  3. API 函数用这个 Session 执行 SQL
  4. 响应返回 → Session 自动提交/回滚 → 连接还回池子

为什么用异步？因为 FastAPI 是异步框架，同步数据库驱动会阻塞事件循环。
为什么用 aiomysql 而不是 pymysql？aiomysql 是异步驱动，pymysql 是同步的。
"""

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# 1. 创建异步数据库引擎 — 管理连接池
#
#    pool_size=10：保持 10 个常驻连接，避免频繁建连
#    max_overflow=20：流量高峰时可以临时多开 20 个（总上限 30）
#    pool_recycle=3600：每小时自动回收连接，防止 MySQL 服务端主动断开旧连接
#    echo=False：生产环境不打印 SQL，调试时改成 True
#
async_engine = create_async_engine(
    settings.database_url,      # 例: mysql+aiomysql://root:123456@127.0.0.1:3306/cueadmin
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    echo=False,
)


# 2. Session 工厂 — 每次调用生成一个新的数据库会话
#
#    expire_on_commit=False：commit 之后 ORM 对象仍然可用
#    因为我们一个请求拿一次数据就返回 JSON 了，不需要再改对象，设 False 省性能
#
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
)


# 3. ORM 基类 — 所有表模型都继承这个
#
#    class User(Base):  → 自动注册到 Base.metadata
#    Base.metadata.create_all() → 一键建表（开发环境用，生产用 Alembic 迁移）
#
class Base(DeclarativeBase):
    pass


# 4. 依赖注入：每个请求自动创建 + 自动关闭 Session
#
#    FastAPI 的 Depends 机制：
#      API 函数参数写 db: DbSession
#      → FastAPI 调用 get_db_session() 拿到 session
#      → API 函数执行完 → async with 退出 → session 自动 close
#      如果中途抛异常 → async with 也会自动 close（类似 try/finally）
#
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


# 5. 类型别名 — 让 API 函数签名更简洁
#
#    之前: async def list_users(db: AsyncSession = Depends(get_db_session))
#    现在: async def list_users(db: DbSession)
#
DbSession = Annotated[AsyncSession, Depends(get_db_session)]

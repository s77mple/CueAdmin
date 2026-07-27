"""数据库核心模块 — 异步引擎与 ORM 基类。"""

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# ---- 异步引擎（连接池管理）----
async_engine = create_async_engine(
    settings.database_url,      # 例: mysql+aiomysql://user:pass@host/db
    pool_size=10,               # 常驻连接数
    max_overflow=20,            # 临时额外连接上限（总上限 30）
    # pool_pre_ping 与 aiomysql 不兼容（ping() 签名差异），用 pool_recycle 替代
    pool_recycle=3600,          # 每小时回收连接，避免服务端主动断开
    echo=False,                 # 不打印 SQL（调试用 True）
)

# ---- Session 工厂 ----
# 每个请求通过 get_db() 创建独立 Session，自动管理事务与连接生命周期
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    expire_on_commit=False,     # commit 后对象仍可用（FastAPI 短请求场景）
)

# ---- ORM 基类 ----
# 所有模型继承此类，自动注册表结构到 metadata
class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends 依赖注入用 — 每个请求创建独立 Session。"""
    async with AsyncSessionLocal() as session:
        yield session


# 复用类型别名的快捷写法：db: DbSession  替代  db: AsyncSession = Depends(get_db)
DbSession = Annotated[AsyncSession, Depends(get_db)]
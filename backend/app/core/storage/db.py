"""
数据库连接 + ORM 基座 — 异步引擎、Session 工厂、模型基类。

FastAPI 的数据库访问模式：
  1. 收到请求 → 从连接池拿一个连接
  2. 创建 Session（一个请求一个 Session，自动开启事务）
  3. API 函数用这个 Session 执行 SQL
  4. 响应返回 → Session 自动提交/回滚 → 连接还回池子

为什么用异步？因为 FastAPI 是异步框架，同步数据库驱动会阻塞事件循环。
为什么用 aiomysql 而不是 pymysql？aiomysql 是异步驱动，pymysql 是同步的。

本文件只放「数据库连接 + ORM 基座」，不含依赖注入；
依赖注入（get_db_session / SessionDep）在 core/dependencies.py，
Redis 连接在 core/storage/redis.py。
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import settings


# 创建异步数据库引擎 — 管理连接池
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


# Session 工厂 — 每次调用生成一个新的数据库会话
#
#    expire_on_commit=False：commit 之后 ORM 对象仍然可用
#    因为我们一个请求拿一次数据就返回 JSON 了，不需要再改对象，设 False 省性能
#
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
)


# ORM 基类 — 所有表模型都继承这个
#
#    class User(Base):  → 自动注册到 Base.metadata
#    Base.metadata.create_all() → 一键建表（开发环境用，生产用 Alembic 迁移）
#
class Base(DeclarativeBase):
    pass


# 时间戳混入 — 为所有表自动添加 created_at / updated_at
#
#    每个表继承 TimestampMixin，自动获得两个时间字段。
#    双重保障：
#      server_default / server_onupdate → 数据库层面，raw SQL 也生效
#      onupdate                         → ORM 层面，Python 代码也能自动更新
#
class TimestampMixin:
    """时间戳混入类 — 不要单独实例化，只用于继承。"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),    # 第一次插入时的默认值
        server_onupdate=func.now(),   # DB 层 UPDATE 时自动更新
        onupdate=func.now(),          # ORM 层 UPDATE 时自动更新
        comment="更新时间",
    )

"""存储基础设施 — 数据库 + Redis 连接。

对外统一从 app.core.storage 导入，内部按存储类型拆文件：
  db.py    数据库引擎、Session 工厂、ORM 基类（Base / TimestampMixin）
  redis.py Redis 连接池状态 + 关闭（close_redis）；获取连接是依赖 get_redis，在 dependencies.py

本包只放「连接资源 + ORM 基座」，不含依赖注入；
依赖注入统一在 core/dependencies.py。
"""

from app.core.storage.db import Base, TimestampMixin, AsyncSessionLocal, async_engine
from app.core.storage.redis import close_redis

__all__ = [
    "async_engine",
    "AsyncSessionLocal",
    "Base",
    "TimestampMixin",
    "close_redis",
]

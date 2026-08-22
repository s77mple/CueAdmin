"""
Redis 连接池状态 — 全局唯一，惰性初始化。

连接池的「获取/初始化」是依赖（get_redis），在 core/dependencies.py；
本文件只保留连接池状态和关闭逻辑（close_redis 由 main.py 的 lifespan 调用）。
"""

import asyncio

import redis.asyncio as aioredis


# 全局 Redis 连接池（整个应用生命周期只有一个，所有请求共享）
_redis_pool: aioredis.Redis | None = None
_redis_lock = asyncio.Lock()  # 防止并发初始化时创建多个连接


async def close_redis() -> None:
    """应用关闭时调用，释放 Redis 连接池。"""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None

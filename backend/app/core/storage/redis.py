"""Redis 客户端工厂 — 客户端由 main.py 的 lifespan 创建/关闭。"""

from redis.asyncio import Redis

from app.core.config import settings


def create_redis() -> Redis:
    """构造 Redis 客户端（此时未连接）。由 lifespan 在启动时调用一次。"""
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,  # 自动把 bytes 转成 str
        socket_connect_timeout=3,  # 3 秒连不上就报错
        # 没连上只是「连不上」，连上了不响应才是更常见的卡死：不设这个，
        # 一个挂住的 Redis 会让每个请求的黑名单/权限缓存查询无限等待（fail-open 变 fail-hang）
        socket_timeout=3,
        socket_keepalive=True,  # 保持长连接
        retry_on_timeout=True,  # 超时自动重试
        health_check_interval=30,  # 每 30 秒检测连接是否存活
    )

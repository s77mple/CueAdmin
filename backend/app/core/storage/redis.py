"""
Redis 客户端工厂 — 连接参数在这里，客户端由 main.py 的 lifespan 创建/关闭。

注意：Redis.from_url() 不建立实际连接，只构造客户端对象；
      真正开 TCP 连接是第一次发命令（ping / get / set ...）时。

本文件只放「Redis 客户端构造」，不含依赖注入；
依赖注入（get_redis / RedisDep）在 core/dependencies.py。
"""

from redis.asyncio import Redis

from app.core.config import settings


def create_redis() -> Redis:
    """构造 Redis 客户端（此时未连接）。由 lifespan 在启动时调用一次。"""
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,  # 自动把 bytes 转成 str
        socket_connect_timeout=3,  # 3 秒连不上就报错
        socket_keepalive=True,  # 保持长连接
        retry_on_timeout=True,  # 超时自动重试
        health_check_interval=30,  # 每 30 秒检测连接是否存活
    )

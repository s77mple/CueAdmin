"""
安全工具 — 密码哈希 + JWT 签发/验证。

数据流：
  注册/改密码 → hash_password(明文) → 存入 users.password_hash
  登录 → verify_password(明文, 哈希) → 返回 True/False
  登录成功 → create_access_token(user_id) → 返回 JWT 字符串
  每次请求 → decode_token(token) → 返回 payload {sub, username, jti, exp, iat}

为什么 bcrypt 要放线程池？
  bcrypt 是纯 CPU 计算，如果在异步线程里同步执行会阻塞事件循环。
  asyncio.to_thread() 把它丢到线程池里跑，不阻塞主循环。
"""

import asyncio
from datetime import datetime, timedelta, timezone

import bcrypt
import uuid
from jose import jwt

from app.core.config import settings


# ============================================================
# 1. 密码哈希 — bcrypt 同步函数（在线程池中异步执行）
# ============================================================

def _hash_password_sync(password: str) -> str:
    """#1a 同步版 — 用 bcrypt 对明文密码做哈希。

    bcrypt 内置 salt（随机盐），每次同密码结果都不同。
    这就是为什么不能用简单的 hash 对比验证密码。
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password_sync(plain_password: str, hashed_password: str) -> bool:
    """#1c 同步版 — 验证明文密码是否与哈希值匹配。

    bcrypt.checkpw 内部会用哈希值里的 salt 重新哈希明文，然后比对。
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


async def hash_password(password: str) -> str:
    """#1b 异步接口 — 将 CPU 密集的 bcrypt 计算放入线程池。"""
    return await asyncio.to_thread(_hash_password_sync, password)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """#1d 异步接口 — 验证密码放入线程池。"""
    return await asyncio.to_thread(_verify_password_sync, plain_password, hashed_password)


# ============================================================
# 2. JWT — 签发与验证
# ============================================================

def create_access_token(user_id: int, username: str) -> str:
    """#2 签发 JWT。

    payload 包含 5 个标准/自定义字段：
      sub:    user_id（JWT 标准，subject = 主体标识）
      username: 用户名（方便 debug 和日志记录）
      jti:    唯一 ID（UUID 十六进制），用于登出时加入黑名单
      iat:    签发时间（issued at）
      exp:    过期时间（expiration）

    过期时间由 settings.jwt_expire_hours 控制（默认 24 小时）。
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "jti": uuid.uuid4().hex,   # 每个 token 一个唯一 ID，登出时用
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """#3 解码 JWT — 验证签名 + 检查过期。

    返回 payload dict = {sub, username, jti, exp, iat}

    调用方需要自行捕获：
      ExpiredSignatureError → 告诉前端 token 过期
      JWTError             → token 无效（签名不对、格式错误）
    """
    from jose import JWTError
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise  # 原样抛出，由上层 distinguish 过期 vs 无效
    except Exception as e:
        raise JWTError(f"Token 解码失败: {e}")

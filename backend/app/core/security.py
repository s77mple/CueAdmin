"""安全工具 — 密码哈希 + JWT 签发/验证。

bcrypt 是纯 CPU 计算，若在异步线程里同步执行会阻塞事件循环，
所以 hash/verify_password 用 asyncio.to_thread 丢线程池执行。
"""

import asyncio
from datetime import datetime, timedelta, timezone

import bcrypt
import uuid
from jose import jwt, JWTError

from app.core.config import settings


# 密码哈希 — bcrypt 同步函数（在线程池中异步执行）

def _hash_password_sync(password: str) -> str:
    """同步版 — bcrypt 内置随机盐，每次同密码结果都不同。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password_sync(plain_password: str, hashed_password: str) -> bool:
    """同步版 — 用哈希值里的 salt 重新哈希明文再比对。"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hash_password_sync, password)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    return await asyncio.to_thread(_verify_password_sync, plain_password, hashed_password)


# JWT — 签发与验证

def _build_token(
    user_id: int,
    username: str,
    token_type: str,
    session_id: str,
    expires_delta: timedelta,
) -> tuple[str, str]:
    """签发一张 JWT，返回 (token, jti)。

    type 区分 access/refresh：refresh 不能当 access 用（dependencies 里断言 type=access）。
    session_id 把同一登录的 access+refresh 绑在一起，登出时按 session_id 撤销 refresh 会话。
    """
    now = datetime.now(timezone.utc)
    jti = uuid.uuid4().hex
    payload = {
        "sub": str(user_id),
        "username": username,
        "jti": jti,
        "type": token_type,
        "session_id": session_id,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm), jti


def create_access_token(user_id: int, username: str, session_id: str) -> str:
    """签发短命 access token（type=access）。"""
    token, _ = _build_token(
        user_id, username, "access", session_id,
        timedelta(minutes=settings.jwt_access_expire_minutes),
    )
    return token


def create_refresh_token(user_id: int, username: str, session_id: str) -> tuple[str, str]:
    """签发长命 refresh token（type=refresh，一次性轮换），返回 (token, jti)。"""
    return _build_token(
        user_id, username, "refresh", session_id,
        timedelta(days=settings.jwt_refresh_expire_days),
    )


def decode_token(token: str) -> dict:
    """解码 JWT — 验证签名 + 检查过期。调用方需自行区分 ExpiredSignatureError / JWTError。"""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise  # 原样抛出（含 ExpiredSignatureError），由上层区分过期 vs 无效
    except Exception as e:
        raise JWTError(f"Token 解码失败: {e}")

"""安全工具：密码哈希 + JWT 签发/验证。"""

import asyncio
from datetime import datetime, timedelta, timezone

import bcrypt
import uuid
from jose import jwt

from app.core.config import settings


def _hash_password_sync(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password_sync(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


async def hash_password(password: str) -> str:
    """异步哈希密码 — bcrypt 是 CPU 密集型，放入线程池执行。"""
    return await asyncio.to_thread(_hash_password_sync, password)


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """异步验证密码。"""
    return await asyncio.to_thread(_verify_password_sync, plain_password, hashed_password)


def create_access_token(user_id: int, username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

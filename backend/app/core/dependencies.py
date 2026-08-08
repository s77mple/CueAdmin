"""
FastAPI 依赖注入模块。

认证 + 鉴权合并到 get_current_user，通过 FastAPI Security scopes 机制声明权限：
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.LIST])]

无 scopes = 只认证不鉴权（/me、/profile 等）：
    user: CurrentUser
"""

import asyncio
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, SecurityScopes
from jose import JWTError, ExpiredSignatureError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import DbSession
from app.models import User, Role
from app.core.security import decode_token
from app.core.exceptions import BusinessException, ErrorCode
from app.core.logger import logger

async def close_redis() -> None:
    """关闭 Redis 连接池（应用关闭时调用）。"""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None


security_scheme = HTTPBearer()

_redis_pool: aioredis.Redis | None = None
_redis_lock = asyncio.Lock()


async def get_redis() -> aioredis.Redis:
    """惰性初始化 Redis 异步连接。"""
    global _redis_pool
    if _redis_pool is None:
        async with _redis_lock:
            if _redis_pool is None:
                _redis_pool = aioredis.Redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=3,
                    socket_keepalive=True,
                )
    return _redis_pool


async def get_current_user(
    security_scopes: SecurityScopes,
    db: DbSession,
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    redis_client: aioredis.Redis = Depends(get_redis),
) -> User:
    """认证 + 鉴权合一。

    security_scopes.scopes 来自路由上 Security(get_current_user, scopes=[...]) 声明。
    未声明 scopes 时只做认证，不校验权限。
    """
    # ---- 1. 解码 JWT ----
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except ExpiredSignatureError:
        raise BusinessException(ErrorCode.AUTH_TOKEN_EXPIRED, "令牌已过期，请重新登录")
    except JWTError:
        raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "令牌无效")

    # ---- 2. Token 黑名单检查（Redis 故障时放行，避免全站不可用）----
    jti = payload.get("jti")
    if not jti:
        raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "令牌无效")
    try:
        if await redis_client.exists(f"blacklist:{jti}"):
            raise BusinessException(ErrorCode.AUTH_TOKEN_REVOKED, "令牌已作废")
    except aioredis.RedisError:
        logger.warning("Redis 不可用，跳过黑名单检查（已登出 token 可能仍有效）")

    # ---- 3. 解析用户 ID ----
    sub = payload.get("sub")
    if sub is None:
        raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "令牌无效")
    try:
        user_id = int(sub)
    except (ValueError, TypeError):
        raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "令牌无效")

    # ---- 4. 权限缓存尝试（仅需要鉴权时）----
    perm_key = f"perm:{user_id}"
    cached_perms: set[str] | None = None
    if security_scopes.scopes:
        try:
            raw = await redis_client.get(perm_key)
            if raw:
                cached_perms = set(raw.split(","))
        except aioredis.RedisError:
            pass

    # ---- 5. 加载用户（命中缓存则跳过权限预加载）----
    stmt = select(User).options(selectinload(User.roles).selectinload(Role.menus))
    if cached_perms is None:
        stmt = stmt.options(selectinload(User.roles).selectinload(Role.permissions))
    stmt = stmt.where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if user is None:
        raise BusinessException(ErrorCode.USER_NOT_FOUND, "用户不存在")
    if not user.is_active:
        raise BusinessException(ErrorCode.USER_NOT_FOUND, "用户已被禁用")
    if not user.roles:
        raise BusinessException(ErrorCode.AUTH_NO_ROLES, "该账号未分配角色")

    # ---- 6. 写入权限缓存（TTL 5 分钟）----
    if cached_perms is None and security_scopes.scopes:
        perms = {p.code for role in user.roles for p in role.permissions}
        try:
            await redis_client.setex(perm_key, 300, ",".join(sorted(perms)))
        except aioredis.RedisError:
            pass

    # ---- 7. 权限校验（仅当路由声明了 scopes 时触发）----
    if security_scopes.scopes:
        # admin 角色拥有所有权限，跳过校验
        if not any(r.code == "admin" for r in user.roles):
            user_perms = cached_perms or {p.code for role in user.roles for p in role.permissions}
            for scope in security_scopes.scopes:
                if scope not in user_perms:
                    logger.bind(user_id=user.id, required=scope).warning("权限不足")
                    raise BusinessException(ErrorCode.ACCESS_DENIED, f"权限不足，需要: {scope}")

    logger.bind(user_id=user.id).debug("用户认证成功")
    return user


# ---- 类型别名 ----

# 仅认证（/me、/profile 等不需要鉴权的接口）
CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    """仅超级管理员可访问 — 直接校验角色码，不走细粒度权限。"""
    if not any(r.code == "admin" for r in user.roles):
        raise BusinessException(ErrorCode.ACCESS_DENIED, "需要管理员权限")
    return user


# 类型别名：admin: RequireAdmin  替代  _=Depends(require_admin)
RequireAdmin = Annotated[User, Depends(require_admin)]

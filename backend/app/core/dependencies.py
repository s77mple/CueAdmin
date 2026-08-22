"""FastAPI 依赖注入模块 — 认证 + 鉴权 + 会话/Redis 依赖。

每个需要登录的请求都会经过 get_current_user：解析 Bearer token → 验证 JWT →
查 Redis 黑名单 → 加载用户/角色/权限 → 可选校验 scopes。权限缓存（perm:{user_id}）
TTL 5 分钟，角色/权限变更时由 service 主动失效。

两种使用方式：
  需要鉴权：user: Annotated[User, Security(get_current_user, scopes=[UserScope.LIST])]
  仅需认证：user: CurrentUser  （/routes 等只需知道"是谁"的接口）
"""

from typing import Annotated, AsyncGenerator

import redis.asyncio as aioredis
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, SecurityScopes
from jose import JWTError, ExpiredSignatureError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.storage import AsyncSessionLocal
from app.core.storage import redis as _redis_store
from app.system.models import User, Role
from app.core.security import decode_token
from app.core.exceptions import BusinessException, ErrorCode
from app.core.logger import logger


# 数据库会话依赖 — 每个请求自动创建 + 自动关闭 Session
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


# Redis 连接依赖 — 懒加载连接池，第一次请求时才创建
async def get_redis() -> aioredis.Redis:
    """懒加载 Redis 连接 — 第一次请求时才创建，启动时不连。"""
    if _redis_store._redis_pool is None:
        async with _redis_store._redis_lock:  # 双重检查锁，确保只建一次
            if _redis_store._redis_pool is None:
                _redis_store._redis_pool = aioredis.Redis.from_url(
                    settings.redis_url,
                    decode_responses=True,        # 自动把 bytes 转成 str
                    socket_connect_timeout=3,      # 3 秒连不上就报错
                    socket_keepalive=True,         # 保持长连接
                    retry_on_timeout=True,         # 超时自动重试
                    health_check_interval=30,      # 每 30 秒检测连接是否存活
                )
    return _redis_store._redis_pool


RedisDep = Annotated[aioredis.Redis, Depends(get_redis)]


# HTTPBearer — 从请求头提取 Bearer Token
security_scheme = HTTPBearer()
BearerTokenDep = Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)]


# 核心依赖：认证 + 鉴权合二为一
async def get_current_user(
    security_scopes: Annotated[SecurityScopes, SecurityScopes()],
    session: SessionDep,
    credentials: BearerTokenDep,
    redis_client: RedisDep,
) -> User:
    """认证 + 鉴权一体化。scopes 为空时只认证不校验权限（/routes 等）。"""

    # ---- 解码 JWT ----
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except ExpiredSignatureError:
        raise BusinessException(ErrorCode.AUTH_TOKEN_EXPIRED, "令牌已过期，请重新登录")
    except JWTError:
        raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "令牌无效")

    # ---- 令牌类型断言：refresh token 不能当 access 用 ----
    if payload.get("type") != "access":
        raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "令牌类型错误")

    # ---- Token 黑名单检查（登出后 jti 进黑名单）----
    # Redis 故障时放行而非拒绝所有请求，这是 fail-open 设计
    jti = payload.get("jti")
    if not jti:
        raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "令牌无效")
    try:
        if await redis_client.exists(f"blacklist:{jti}"):
            raise BusinessException(ErrorCode.AUTH_TOKEN_REVOKED, "令牌已作废")
    except aioredis.RedisError:
        logger.warning("Redis 不可用，跳过黑名单检查（已登出 token 可能仍有效）")

    # ---- 解析用户 ID ----
    sub = payload.get("sub")
    if sub is None:
        raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "令牌无效")
    try:
        user_id = int(sub)
    except (ValueError, TypeError):
        raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "令牌无效")

    # ---- 尝试 Redis 权限缓存（只有需要鉴权的请求才读）----
    perm_key = f"perm:{user_id}"
    cached_perms: set[str] | None = None
    if security_scopes.scopes:
        try:
            raw = await redis_client.get(perm_key)
            if raw:
                cached_perms = set(raw.split(","))  # 缓存格式：逗号分隔的权限 code
        except aioredis.RedisError:
            pass  # Redis 故障时走 DB，不阻塞请求

    # ---- 从数据库加载用户 + 角色 + 菜单 ----
    stmt = select(User).options(selectinload(User.roles).selectinload(Role.menus))
    # 缓存命中 → 权限用缓存的；未命中 → 权限和菜单都从 DB 加载
    if cached_perms is None:
        stmt = stmt.options(selectinload(User.roles).selectinload(Role.permissions))
    stmt = stmt.where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalars().first()

    # ---- 校验用户状态 ----
    if user is None:
        raise BusinessException(ErrorCode.USER_NOT_FOUND, "用户不存在")
    if not user.is_active:
        raise BusinessException(ErrorCode.USER_NOT_FOUND, "用户已被禁用")
    if not user.roles:
        raise BusinessException(ErrorCode.AUTH_NO_ROLES, "该账号未分配角色")

    # ---- 写入权限缓存（TTL 5 分钟）----
    if cached_perms is None and security_scopes.scopes:
        perms = {p.code for role in user.roles for p in role.permissions}
        try:
            await redis_client.setex(perm_key, 300, ",".join(sorted(perms)))
            # 5 分钟内权限变更要等缓存过期；角色/权限变更时 service 会主动 invalidate
        except aioredis.RedisError:
            pass  # 写缓存失败不影响请求

    # ---- 权限校验（仅路由声明了 scopes 时触发）----
    if security_scopes.scopes:
        # admin 角色拥有所有权限，直接放行
        if not any(r.code == "admin" for r in user.roles):
            user_perms = cached_perms or {p.code for role in user.roles for p in role.permissions}
            for scope in security_scopes.scopes:
                if scope not in user_perms:
                    logger.bind(user_id=user.id, required=scope).warning("权限不足")
                    raise BusinessException(ErrorCode.ACCESS_DENIED, f"权限不足，需要: {scope}")

    logger.bind(user_id=user.id).debug("用户认证成功")
    return user


# 便捷类型别名
CurrentUser = Annotated[User, Depends(get_current_user)]  # 仅认证不鉴权（/routes 等）


async def require_admin(user: CurrentUser) -> User:
    """仅管理员可访问 — 不走细粒度权限，直接检查是否有 admin 角色。"""
    if not any(r.code == "admin" for r in user.roles):
        raise BusinessException(ErrorCode.ACCESS_DENIED, "需要管理员权限")
    return user


RequireAdmin = Annotated[User, Depends(require_admin)]

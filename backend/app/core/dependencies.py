"""
FastAPI 依赖注入模块 — 认证 + 鉴权的核心入口。

这是整个后端最重要的文件，每个需要登录的请求都会经过这里。
一个完整的请求认证流程（以 GET /api/v1/users 为例）：

  #1 浏览器发请求，带 Authorization: Bearer <token>
  #2 HTTPBearer() 从请求头解析出 token 字符串
  #3 decode_token() 验证 JWT 签名 + 是否过期
  #4 检查 Redis 黑名单：这个 token 有没有被登出作废？
  #5 从 token 的 sub 字段取出 user_id
  #6 尝试从 Redis 读取权限缓存（key = perm:{user_id}）
    ├─ 命中 → 拿缓存的权限集合，省一次 DB 查询
    └─ 未命中 → 从 DB 加载用户+角色+权限+菜单
  #7 用户不存在/已禁用/无角色 → 拒绝请求
  #8 缓存命中 → 跳过权限写入；未命中 → 写入 Redis（TTL 5 分钟）
  #9 路由声明了 scopes → 校验权限（admin 角色直接放行）
  #10 返回 User 对象，注入到 API 函数的 user 参数

两种使用方式：
  需要鉴权：user: Annotated[User, Security(get_current_user, scopes=[UserScope.LIST])]
  仅需认证：user: CurrentUser  （/routes 等只需知道"是谁"的接口）
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


# ============================================================
# 1. Redis 连接管理 — 惰性初始化 + 应用关闭时释放
# ============================================================

# 全局 Redis 连接池（整个应用生命周期只有一个，所有请求共享）
_redis_pool: aioredis.Redis | None = None
_redis_lock = asyncio.Lock()  # 防止并发初始化时创建多个连接


async def close_redis() -> None:
    """#1b 应用关闭时调用，释放 Redis 连接池。"""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None


async def get_redis() -> aioredis.Redis:
    """#1a 懒加载 Redis 连接 — 第一次请求时才创建，启动时不连。"""
    global _redis_pool
    if _redis_pool is None:
        async with _redis_lock:  # 双重检查锁，确保只建一次
            if _redis_pool is None:
                _redis_pool = aioredis.Redis.from_url(
                    settings.redis_url,
                    decode_responses=True,        # 自动把 bytes 转成 str
                    socket_connect_timeout=3,      # 3 秒连不上就报错
                    socket_keepalive=True,         # 保持长连接
                    retry_on_timeout=True,         # 超时自动重试
                    health_check_interval=30,      # 每 30 秒检测连接是否存活
                )
    return _redis_pool


# ============================================================
# 2. HTTPBearer — 从请求头提取 Bearer Token
# ============================================================

security_scheme = HTTPBearer()
# 前端在 axios 拦截器里给每个请求加了 Authorization: Bearer xxx
# HTTPBearer 自动解析这个头，拿到的 credentials.credentials 就是 token 字符串


# ============================================================
# 3. 核心依赖：认证 + 鉴权合二为一
# ============================================================

async def get_current_user(
    security_scopes: SecurityScopes,                              # FastAPI 自动注入 scopes 列表
    session: DbSession,                                                # 数据库会话（自动注入）
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),  # token（自动注入）
    redis_client: aioredis.Redis = Depends(get_redis),            # Redis（自动注入）
) -> User:
    """#3 认证 + 鉴权一体化。

    路由上写 Security(get_current_user, scopes=[...]) 声明需要的权限，
    scopes 为空时只做认证不校验权限（/routes 等接口）。
    """

    # ---- #3.1 解码 JWT ----
    token = credentials.credentials
    try:
        payload = decode_token(token)  # 验证签名 + 过期时间
    except ExpiredSignatureError:
        # JWT 已过期 → 前端收到 11002 → 跳转登录页
        raise BusinessException(ErrorCode.AUTH_TOKEN_EXPIRED, "令牌已过期，请重新登录")
    except JWTError:
        raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "令牌无效")

    # ---- #3.2 Token 黑名单检查 ----
    # 用户登出时会把 token 的 jti 存入 Redis 黑名单
    # Redis 故障时放行（而不是拒绝所有请求），这是 fail-open 设计
    jti = payload.get("jti")         # JWT ID：每个 token 的唯一标识
    if not jti:
        raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "令牌无效")
    try:
        if await redis_client.exists(f"blacklist:{jti}"):
            raise BusinessException(ErrorCode.AUTH_TOKEN_REVOKED, "令牌已作废")
    except aioredis.RedisError:
        logger.warning("Redis 不可用，跳过黑名单检查（已登出 token 可能仍有效）")

    # ---- #3.3 解析用户 ID ----
    sub = payload.get("sub")         # sub = subject = 用户 ID
    if sub is None:
        raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "令牌无效")
    try:
        user_id = int(sub)
    except (ValueError, TypeError):
        raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "令牌无效")

    # ---- #3.4 尝试 Redis 权限缓存 ----
    # 只有需要鉴权的请求才读缓存（/me 不需要权限信息）
    perm_key = f"perm:{user_id}"
    cached_perms: set[str] | None = None
    if security_scopes.scopes:
        try:
            raw = await redis_client.get(perm_key)
            if raw:
                # 缓存格式：逗号分隔的权限 code 字符串
                # 例如 "user:list,user:create,role:list"
                cached_perms = set(raw.split(","))
        except aioredis.RedisError:
            pass  # Redis 故障时走 DB，不阻塞请求

    # ---- #3.5 从数据库加载用户 + 角色 + 菜单 ----
    stmt = select(User).options(selectinload(User.roles).selectinload(Role.menus))
    # 如果缓存命中 → 只加载菜单（权限用缓存的），省掉 permissions 的 JOIN
    # 如果缓存未命中 → 权限和菜单都要从 DB 加载
    if cached_perms is None:
        stmt = stmt.options(selectinload(User.roles).selectinload(Role.permissions))
    stmt = stmt.where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalars().first()

    # ---- #3.6 校验用户状态 ----
    if user is None:
        raise BusinessException(ErrorCode.USER_NOT_FOUND, "用户不存在")
    if not user.is_active:
        raise BusinessException(ErrorCode.USER_NOT_FOUND, "用户已被禁用")
    if not user.roles:
        raise BusinessException(ErrorCode.AUTH_NO_ROLES, "该账号未分配角色")

    # ---- #3.7 写入 Redis 权限缓存（TTL 5 分钟）----
    if cached_perms is None and security_scopes.scopes:
        # 从所有角色收集权限 code，去重后存 Redis
        perms = {p.code for role in user.roles for p in role.permissions}
        try:
            await redis_client.setex(perm_key, 300, ",".join(sorted(perms)))
            # TTL=300 秒：5 分钟内用户权限变更需要等缓存过期
            # 角色/权限变更时 active invalidate：见 roles.py 的 _clear_role_users_cache()
        except aioredis.RedisError:
            pass  # 写缓存失败不影响请求

    # ---- #3.8 权限校验（仅路由声明了 scopes 时触发）----
    if security_scopes.scopes:
        # admin 角色拥有所有权限，直接放行（不走细粒度权限校验）
        if not any(r.code == "admin" for r in user.roles):
            # 优先用缓存的权限集合，否则从 ORM 对象现算
            user_perms = cached_perms or {p.code for role in user.roles for p in role.permissions}
            # 逐一检查每个 scope（只要缺一个就拒绝）
            for scope in security_scopes.scopes:
                if scope not in user_perms:
                    logger.bind(user_id=user.id, required=scope).warning("权限不足")
                    raise BusinessException(ErrorCode.ACCESS_DENIED, f"权限不足，需要: {scope}")

    logger.bind(user_id=user.id).debug("用户认证成功")
    return user  # 返回 User ORM 对象，注入到 API 函数的 user 参数


# ============================================================
# 4. 便捷类型别名 — 让 API 函数签名更简洁
# ============================================================

# 仅认证不鉴权：`user: CurrentUser`
# 用于 /routes 等只需要知道"是谁"的接口
CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(user: CurrentUser) -> User:
    """#4 仅管理员可访问 — 不走细粒度权限，直接检查是否有 admin 角色。"""
    if not any(r.code == "admin" for r in user.roles):
        raise BusinessException(ErrorCode.ACCESS_DENIED, "需要管理员权限")
    return user


# `admin: RequireAdmin` 比 `_=Depends(require_admin)` 更优雅
RequireAdmin = Annotated[User, Depends(require_admin)]

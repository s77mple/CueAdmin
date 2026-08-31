"""认证业务逻辑 — 登录 + 刷新令牌。

用户不存在时也对假哈希跑一次 bcrypt，防止通过响应时间差枚举用户名。
登录响应不含 menus —— 菜单统一收口到 collect_user_menus()，由 /routes 下发。

refresh token 采用「一次性轮换 + 复用检测」：
  - 每换一次票，旧 refresh 作废、签发新 refresh（接力棒一次性）
  - 若有人拿已作废的 refresh 再来换票 → 判定被盗 → 撤销整个会话（复用检测）
"""

import uuid
from datetime import timedelta

import redis.asyncio as aioredis
from jose import JWTError, ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BusinessException, ErrorCode
from app.core.logger import logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.system.repositories import UserRepository
from app.system.schemas.auth import LoginResponse, RefreshResponse
from app.system.schemas.user import UserRead


# 假哈希 — 用户不存在时也跑一次 bcrypt，防止时间差枚举用户名
# 这是已知明文 bcrypt("a") 的结果
_DUMMY_HASH = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"


class AuthService:
    """登录 + 刷新令牌业务编排。"""

    def __init__(self, session: AsyncSession, redis_client: aioredis.Redis | None = None):
        self.session = session
        self.redis = redis_client
        self.users = UserRepository(session)

    async def login(self, username: str, password: str, client: str | None = None) -> LoginResponse:

        # ---- 一次查询预加载所有关联数据 ----
        # get_for_login 里用 selectinload 一次带出 roles + permissions，避免 N+1
        # 菜单不在这里加载：登录响应不含 menus，动态路由统一走 /routes
        user = await self.users.get_for_login(username)

        # ---- 防用户名枚举 ----
        # 用户不存在也跑一次 bcrypt（约 100ms），让攻击者无法靠响应时间判断用户名是否存在
        if user is None:
            await verify_password(password, _DUMMY_HASH)
            raise BusinessException(ErrorCode.AUTH_INVALID_CREDENTIALS, "用户名或密码错误")

        # ---- 验证密码 ----
        if not await verify_password(password, user.password_hash):
            raise BusinessException(ErrorCode.AUTH_INVALID_CREDENTIALS, "用户名或密码错误")

        # ---- 检查是否有角色 ----
        if not user.roles:
            raise BusinessException(ErrorCode.AUTH_NO_ROLES, "该账号未分配角色，请联系管理员")

        # ---- 收集权限 ----
        permissions = sorted({perm.code for role in user.roles for perm in role.permissions})

        # ---- 签发 access + refresh，并把 refresh 会话写入 Redis ----
        # session_id 把 access/refresh 绑到同一次登录，登出时按它撤销 refresh 会话
        session_id = uuid.uuid4().hex
        access_token = create_access_token(user.id, user.username, session_id)
        refresh_token, refresh_jti = create_refresh_token(user.id, user.username, session_id)
        if self.redis is not None:
            try:
                await self.redis.setex(
                    f"session:{session_id}",
                    timedelta(days=settings.jwt_refresh_expire_days),
                    refresh_jti,
                )
            except aioredis.RedisError:
                # Redis 故障时 refresh 换票不可用，但 access 仍能正常用（fail-open）
                logger.warning("Redis 不可用，refresh 会话未存储")

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserRead.model_validate(user),
            permissions=permissions,
            roles=[{"id": r.id, "code": r.code, "name": r.name} for r in user.roles],
        )

    async def refresh(self, refresh_token: str) -> RefreshResponse:
        """用 refresh token 换新 access + 新 refresh（轮换 + 复用检测）。"""
        try:
            payload = decode_token(refresh_token)
        except ExpiredSignatureError:
            raise BusinessException(ErrorCode.AUTH_TOKEN_EXPIRED, "登录已过期，请重新登录")
        except JWTError:
            raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "刷新令牌无效")

        if payload.get("type") != "refresh":
            raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "令牌类型错误")

        session_id = payload.get("session_id")
        jti = payload.get("jti")
        if not session_id or not jti:
            raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "刷新令牌无效")

        if self.redis is None:
            raise BusinessException(ErrorCode.AUTH_SERVICE_UNAVAILABLE, "刷新服务暂不可用")

        key = f"session:{session_id}"
        try:
            current_jti = await self.redis.get(key)
        except aioredis.RedisError:
            raise BusinessException(ErrorCode.AUTH_SERVICE_UNAVAILABLE, "刷新服务暂不可用")

        # 会话不存在：已过期 / 已登出 / 已被撤销
        if current_jti is None:
            raise BusinessException(ErrorCode.AUTH_TOKEN_EXPIRED, "登录已过期，请重新登录")

        # 复用检测：这张 refresh 已被轮换掉、现在又出现 → 判定被盗，撤销整个会话
        if current_jti != jti:
            try:
                await self.redis.delete(key)
            except aioredis.RedisError:
                pass
            logger.warning(f"检测到 refresh token 复用，已撤销会话 {session_id}")
            raise BusinessException(ErrorCode.AUTH_TOKEN_REVOKED, "检测到账号异常，请重新登录")

        # 校验用户仍存在且启用（封号即时生效，不被 refresh 绕过）
        try:
            user_id = int(payload["sub"])
        except (ValueError, TypeError):
            raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "刷新令牌无效")

        user = await self.users.get_active(user_id)
        if user is None:
            try:
                await self.redis.delete(key)
            except aioredis.RedisError:
                pass
            raise BusinessException(ErrorCode.AUTH_TOKEN_INVALID, "账号已失效")

        # 轮换：旧 refresh 作废，签发新 access + 新 refresh，会话指向新 jti
        username = payload.get("username", "")
        new_access = create_access_token(user.id, username, session_id)
        new_refresh, new_jti = create_refresh_token(user.id, username, session_id)
        try:
            await self.redis.setex(
                key, timedelta(days=settings.jwt_refresh_expire_days), new_jti
            )
        except aioredis.RedisError:
            raise BusinessException(ErrorCode.AUTH_SERVICE_UNAVAILABLE, "刷新服务暂不可用")

        return RefreshResponse(access_token=new_access, refresh_token=new_refresh)

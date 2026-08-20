"""
认证 API — 登录 / 登出。

前端登录的完整交互流程：

  #1 用户在登录页输入用户名密码
  #2 POST /api/v1/auth/login → 成功返回 { access_token, user, permissions, roles }
  #3 前端把 access_token 存 localStorage
  #4 后续所有请求，axios 拦截器自动在 header 加 Authorization: Bearer <token>
  #5 每次路由跳转，vue-router 守卫调用 initRouter()，从 GET /api/v1/routes 拿动态路由（菜单不随登录下发）
  #6 每个管理页面通过 v-perms="['user:list']" 控制按钮显隐
  #7 点击登出 → POST /api/v1/auth/logout → token 加入 Redis 黑名单 + 清除权限缓存
"""

import time
import redis.asyncio as aioredis
from fastapi import APIRouter
from jose import JWTError

from app.core.database import SessionDep
from app.core.dependencies import BearerTokenDep, RedisDep
from app.core.security import decode_token
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.response import ApiResponse
from app.services.auth_service import AuthService
from app.core.logger import logger
from app.core.exceptions import BusinessException, ErrorCode

router = APIRouter()


# ============================================================
# 1. 登录频率限制 — 5 次失败 / 5 分钟 → 锁定 15 分钟
# ============================================================

_LOGIN_MAX_FAILURES = 5     # 最大失败次数
_LOGIN_FAIL_WINDOW = 300    # 失败计数窗口（5 分钟）
_LOGIN_LOCK_TTL = 900       # 锁定时间（15 分钟）


# ============================================================
# 2. POST /auth/login — 登录
# ============================================================

@router.post("/login", response_model=ApiResponse[LoginResponse])
async def login(
    body: LoginRequest,                                    # 前端传来的 { username, password }
    session: SessionDep,                                         # 数据库会话（自动注入）
    redis_client: RedisDep,     # Redis（自动注入）
) -> ApiResponse[LoginResponse]:
    """#2 登录接口。

    流程：
      a. 检查是否被锁定（Redis key: login_fail:{username}）
      b. 调用 AuthService.login() 执行认证逻辑
      c. 成功 → 清除失败计数 + 清除旧权限缓存 + 返回 token+用户信息
      d. 失败 → 增加失败计数（Redis INCR），达阈值锁定 15 分钟
    """

    fail_key = f"login_fail:{body.username}"

    # ---- #2a 检查是否被锁定 ----
    try:
        fail_count = await redis_client.get(fail_key)
        if fail_count is not None and int(fail_count) >= _LOGIN_MAX_FAILURES:
            raise BusinessException(
                ErrorCode.AUTH_INVALID_CREDENTIALS,
                f"登录失败次数过多，请 {_LOGIN_LOCK_TTL // 60} 分钟后重试",
            )
    except aioredis.RedisError:
        pass  # Redis 故障时跳过频率限制，不阻塞登录

    # ---- #2b-c-d 执行登录 + 处理结果 ----
    try:
        result = await AuthService(session).login(body.username, body.password, body.client)
    except BusinessException as e:
        if e.code == ErrorCode.AUTH_INVALID_CREDENTIALS:
            # 登录失败 → 增加计数器
            try:
                new_count = await redis_client.incr(fail_key)  # 原子递增
                if new_count == 1:
                    await redis_client.expire(fail_key, _LOGIN_FAIL_WINDOW)  # 首次失败设 5 分钟窗口
                if new_count >= _LOGIN_MAX_FAILURES:
                    await redis_client.expire(fail_key, _LOGIN_LOCK_TTL)     # 达阈值 → 延长到 15 分钟
                    logger.bind(username=body.username).warning(
                        f"登录失败 {new_count} 次，锁定 {_LOGIN_LOCK_TTL // 60} 分钟"
                    )
            except aioredis.RedisError:
                pass  # Redis 故障不影响登录流程
        raise  # 错误继续上抛，由全局 handler 捕获

    # ---- #2c 登录成功 → 清除失败计数 + 旧权限缓存 ----
    try:
        await redis_client.delete(fail_key)                 # 清除失败计数
        await redis_client.delete(f"perm:{result.user.id}") # 清除旧权限缓存（确保登录后权限是最新的）
    except aioredis.RedisError:
        logger.warning("登录时清除缓存失败，跳过")
    logger.bind(username=body.username).info("用户登录成功")
    return ApiResponse.ok(data=result)


# ============================================================
# 3. POST /auth/logout — 登出
# ============================================================

@router.post("/logout", response_model=ApiResponse)
async def logout(
    credentials: BearerTokenDep,                           # 从请求头取 Bearer token
    redis_client: RedisDep,
) -> ApiResponse:
    """#3 登出接口。

    为什么登出要后端参与？JWT 是无状态的，无法主动失效。
    所以把 token 的 jti 加入 Redis 黑名单，后续请求在 dependencies.py #3.2 被拦截。

    TTL = token 剩余有效期，过期后 Redis 自动删除，不占内存。
    """
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        # Token 已无效（过期或损坏），无需加入黑名单
        return ApiResponse.ok(message="已登出")

    jti = payload.get("jti")         # token 唯一 ID
    user_id = payload.get("sub")
    exp = payload.get("exp")
    # TTL = 距离 token 过期还剩多少秒，至少 1 秒
    ttl = max(int(exp - time.time()), 1) if exp else 86400
    try:
        if jti:
            await redis_client.setex(f"blacklist:{jti}", ttl, "1")  # 加入黑名单
        if user_id:
            await redis_client.delete(f"perm:{user_id}")             # 清除权限缓存
    except aioredis.RedisError:
        logger.warning("登出时 Redis 操作失败，跳过")
    return ApiResponse.ok(message="已登出")

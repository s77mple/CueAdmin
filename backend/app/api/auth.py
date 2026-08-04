"""认证 API"""

import time
import redis.asyncio as aioredis
from fastapi import APIRouter, Body, Depends
from jose import JWTError
from sqlalchemy import select

from app.core.database import DbSession
from app.core.dependencies import CurrentUser, get_redis, security_scheme
from app.core.security import decode_token
from app.models import User, Menu
from app.schemas.auth import LoginRequest, LoginApiResponse, MeApiResponse, MeResponse
from app.schemas.response import ApiResponse
from app.services.auth_service import AuthService
from app.core.logger import logger
from app.core.exceptions import BusinessException, ErrorCode

router = APIRouter()


# 登录频率限制：5 次失败 / 5 分钟 → 锁定 15 分钟
_LOGIN_MAX_FAILURES = 5
_LOGIN_FAIL_WINDOW = 300   # 5 分钟
_LOGIN_LOCK_TTL = 900      # 15 分钟


@router.post("/login", response_model=LoginApiResponse)
async def login(
    body: LoginRequest,
    db: DbSession,
    redis_client: aioredis.Redis = Depends(get_redis),
):
    fail_key = f"login_fail:{body.username}"

    # 检查是否已锁定
    try:
        fail_count = await redis_client.get(fail_key)
        if fail_count is not None and int(fail_count) >= _LOGIN_MAX_FAILURES:
            raise BusinessException(
                ErrorCode.AUTH_INVALID_CREDENTIALS,
                f"登录失败次数过多，请 {_LOGIN_LOCK_TTL // 60} 分钟后重试",
            )
    except aioredis.RedisError:
        pass  # Redis 不可用时跳过频率限制，不影响登录

    try:
        result = await AuthService(db).login(body.username, body.password, body.client)
    except BusinessException as e:
        if e.code == ErrorCode.AUTH_INVALID_CREDENTIALS:
            # 记录失败次数（滑动窗口）
            try:
                new_count = await redis_client.incr(fail_key)
                if new_count == 1:
                    await redis_client.expire(fail_key, _LOGIN_FAIL_WINDOW)
                if new_count >= _LOGIN_MAX_FAILURES:
                    await redis_client.expire(fail_key, _LOGIN_LOCK_TTL)
                    logger.bind(username=body.username).warning(
                        f"登录失败 {new_count} 次，锁定 {_LOGIN_LOCK_TTL // 60} 分钟"
                    )
            except aioredis.RedisError:
                pass
        raise

    # 登录成功，清除失败计数
    try:
        await redis_client.delete(fail_key)
        await redis_client.delete(f"perm:{result.user.id}")
    except aioredis.RedisError:
        logger.warning("登录时清除缓存失败，跳过")
    logger.bind(username=body.username).info("用户登录成功")
    return ApiResponse.ok(data=result)


@router.post("/logout", response_model=ApiResponse)
async def logout(
    credentials=Depends(security_scheme),
    redis_client: aioredis.Redis = Depends(get_redis),
):
    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        # Token 无效（可能已过期），无需加入黑名单
        return ApiResponse.ok(message="已登出")

    jti = payload.get("jti")
    user_id = payload.get("sub")
    exp = payload.get("exp")
    ttl = max(int(exp - time.time()), 1) if exp else 86400
    try:
        if jti:
            await redis_client.setex(f"blacklist:{jti}", ttl, "1")
        if user_id:
            await redis_client.delete(f"perm:{user_id}")
    except aioredis.RedisError:
        logger.warning("登出时 Redis 操作失败，跳过")
    return ApiResponse.ok(message="已登出")


@router.put("/profile", response_model=ApiResponse)
async def update_profile(
    db: DbSession,
    user: CurrentUser,
    display_name: str = Body(..., embed=True, max_length=50),
):
    user.display_name = display_name
    await db.commit()
    return ApiResponse.ok(data={"display_name": user.display_name})


@router.get("/me", response_model=MeApiResponse)
async def me(user: CurrentUser, db: DbSession):
    permissions = sorted({p.code for role in user.roles for p in role.permissions})
    # 系统角色（admin）拥有全部菜单权限
    if any(role.is_system for role in user.roles):
        stmt = select(Menu).order_by(Menu.sort_order, Menu.id)
        result = await db.execute(stmt)
        all_menus = result.scalars().all()
        menus = [
            {
                "code": m.code, "name": m.name, "icon": m.icon, "path": m.path,
                "component": m.component,
                "parent_id": m.parent_id, "sort_order": m.sort_order,
            }
            for m in all_menus
        ]
    else:
        seen: set[str] = set()
        menus: list[dict] = []
        for role in user.roles:
            for m in role.menus:
                if m.code not in seen:
                    seen.add(m.code)
                    menus.append({
                        "code": m.code, "name": m.name, "icon": m.icon, "path": m.path,
                        "component": m.component,
                        "parent_id": m.parent_id, "sort_order": m.sort_order,
                    })
    menus.sort(key=lambda m: m["sort_order"])
    return ApiResponse.ok(data=MeResponse(
        user=user,
        permissions=permissions,
        roles=[{"id": r.id, "code": r.code, "name": r.name} for r in user.roles],
        menus=menus,
    ))

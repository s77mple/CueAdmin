"""认证 API"""

import time
import redis.asyncio as aioredis
from fastapi import APIRouter, Body, Depends

from app.core.database import DbSession
from app.core.dependencies import CurrentUser, get_redis, security_scheme
from app.core.security import decode_token
from app.schemas.auth import LoginRequest, LoginApiResponse, MeApiResponse, MeResponse
from app.schemas.response import ApiResponse
from app.services.auth_service import AuthService
from app.core.logger import logger

router = APIRouter()


@router.post("/login", response_model=LoginApiResponse)
async def login(
    body: LoginRequest,
    db: DbSession,
    redis_client: aioredis.Redis = Depends(get_redis),
):
    result = await AuthService(db).login(body.username, body.password, body.client)
    try:
        await redis_client.delete(f"perm:{result.user.id}")
    except Exception:
        pass
    logger.bind(username=body.username).info("用户登录成功")
    return ApiResponse.ok(data=result)


@router.post("/logout", response_model=ApiResponse)
async def logout(
    credentials=Depends(security_scheme),
    redis_client: aioredis.Redis = Depends(get_redis),
):
    try:
        payload = decode_token(credentials.credentials)
        jti = payload.get("jti")
        user_id = payload.get("sub")
        exp = payload.get("exp")
        ttl = max(int(exp - time.time()), 1) if exp else 86400
        if jti:
            await redis_client.setex(f"blacklist:{jti}", ttl, "1")
        if user_id:
            await redis_client.delete(f"perm:{user_id}")
    except Exception as e:
        logger.warning("登出清理失败: {}", e)
    return ApiResponse.ok(message="已登出")


@router.put("/profile", response_model=ApiResponse)
async def update_profile(
    db: DbSession,
    user: CurrentUser,
    display_name: str = Body(..., embed=True),
):
    user.display_name = display_name
    await db.commit()
    return ApiResponse.ok(data={"display_name": user.display_name})


@router.get("/me", response_model=MeApiResponse)
async def me(user: CurrentUser):
    permissions = sorted({p.code for role in user.roles for p in role.permissions})
    seen: set[str] = set()
    menus: list[dict] = []
    for role in user.roles:
        for m in role.menus:
            if m.code not in seen:
                seen.add(m.code)
                menus.append({
                    "code": m.code, "name": m.name, "icon": m.icon, "path": m.path,
                    "parent_id": m.parent_id, "sort_order": m.sort_order,
                })
    return ApiResponse.ok(data=MeResponse(
        user=user,
        permissions=permissions,
        roles=[{"id": r.id, "code": r.code, "name": r.name} for r in user.roles],
        menus=menus,
    ))

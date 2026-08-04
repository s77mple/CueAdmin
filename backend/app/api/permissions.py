"""权限码管理 API"""

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Security
from sqlalchemy import select

from app.core.database import DbSession
from app.core.dependencies import get_current_user, get_redis
from app.core.exceptions import BusinessException, ErrorCode
from app.models import Permission, User
from app.models.associations import user_roles, role_permissions
from app.schemas.permission import PermissionCreate, PermissionUpdate, PermissionListResponse, PermissionListApiResponse, PermissionBriefResponse
from app.schemas.response import ApiResponse
from app.core.logger import logger

router = APIRouter()


async def _clear_perm_cache(db: DbSession, redis_client: aioredis.Redis, perm_id: int):
    """删除权限或修改 code 后，清除所有关联用户的权限缓存。"""
    rows = (await db.execute(
        select(user_roles.c.user_id)
        .join(role_permissions, role_permissions.c.role_id == user_roles.c.role_id)
        .where(role_permissions.c.permission_id == perm_id)
        .distinct()
    )).all()
    for (uid,) in rows:
        try:
            await redis_client.delete(f"perm:{uid}")
        except aioredis.RedisError:
            pass
    if rows:
        logger.info("权限变更，已清除 {} 个用户缓存", len(rows))


class PermissionScope:
    LIST   = "permission:list"
    CREATE = "permission:create"
    UPDATE = "permission:update"
    DELETE = "permission:delete"


@router.get("", response_model=PermissionListApiResponse, summary="权限列表")
async def list_permissions(
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.LIST])],
):
    result = await db.execute(
        select(Permission).order_by(Permission.resource, Permission.action)
    )
    perms = result.scalars().all()
    data = PermissionListResponse(
        items=[
            {
                "id": p.id, "code": p.code, "name": p.name,
                "resource": p.resource, "action": p.action,
                "description": p.description,
            }
            for p in perms
        ],
        total=len(perms),
    )
    return ApiResponse.ok(data=data)


@router.post("", response_model=PermissionBriefResponse, status_code=201, summary="创建权限")
async def create_permission(
    body: PermissionCreate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.CREATE])],
):
    if (await db.execute(select(Permission).where(Permission.code == body.code))).scalars().first():
        raise BusinessException(ErrorCode.PERM_CODE_EXISTS, "权限编码已存在")
    perm = Permission(
        code=body.code, name=body.name,
        resource=body.resource, action=body.action,
        description=body.description,
    )
    db.add(perm)
    await db.commit()
    await db.refresh(perm)
    return ApiResponse.ok(data=perm, message="创建成功")


@router.put("/{perm_id}", response_model=PermissionBriefResponse, summary="更新权限")
async def update_permission(
    perm_id: int,
    body: PermissionUpdate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.UPDATE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    result = await db.execute(
        select(Permission).where(Permission.id == perm_id).with_for_update()
    )
    perm = result.scalars().first()
    if not perm:
        raise BusinessException(ErrorCode.PERM_NOT_FOUND, f"权限不存在: {perm_id}")
    code_changed = False
    if body.code is not None and body.code != perm.code:
        if (await db.execute(select(Permission).where(Permission.code == body.code))).scalars().first():
            raise BusinessException(ErrorCode.PERM_CODE_EXISTS, "权限编码已存在")
        perm.code = body.code
        code_changed = True
    if body.name is not None:
        perm.name = body.name
    if body.resource is not None:
        perm.resource = body.resource
    if body.action is not None:
        perm.action = body.action
    if body.description is not None:
        perm.description = body.description
    await db.commit()
    if code_changed:
        await _clear_perm_cache(db, redis_client, perm_id)
    return ApiResponse.ok(data=perm, message="更新成功")


@router.delete("/{perm_id}", response_model=ApiResponse, summary="删除权限")
async def delete_permission(
    perm_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.DELETE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    result = await db.execute(
        select(Permission).where(Permission.id == perm_id).with_for_update()
    )
    perm = result.scalars().first()
    if not perm:
        raise BusinessException(ErrorCode.PERM_NOT_FOUND, f"权限不存在: {perm_id}")
    await _clear_perm_cache(db, redis_client, perm_id)  # 删前清除（删后关联表 CASCADE 查不到）
    await db.delete(perm)
    await db.commit()
    return ApiResponse.ok(message="删除成功")

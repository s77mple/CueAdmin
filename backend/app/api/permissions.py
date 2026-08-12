"""
权限码管理 API — 薄控制器，业务逻辑全部委托给 PermissionService。
"""

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query, Security

from app.core.database import DbSession
from app.core.dependencies import get_current_user, get_redis
from app.models import User
from app.schemas.permission import (
    PermissionCreate, PermissionUpdate, PermissionPatch,
    PermissionListApiResponse, PermissionBriefResponse,
)
from app.schemas.response import ApiResponse
from app.services.permission_service import PermissionService

router = APIRouter()


class PermissionScope:
    LIST   = "permission:list"
    CREATE = "permission:create"
    UPDATE = "permission:update"
    DELETE = "permission:delete"


# ============================================================
# GET /permissions — 权限列表
# ============================================================

@router.get("", response_model=PermissionListApiResponse, summary="权限列表")
async def list_permissions(
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.LIST])],
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
):
    result = await PermissionService(db).list_permissions(page, page_size)
    return ApiResponse.ok(data=result)


# ============================================================
# POST /permissions — 创建权限
# ============================================================

@router.post("", response_model=PermissionBriefResponse, status_code=201, summary="创建权限")
async def create_permission(
    body: PermissionCreate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.CREATE])],
):
    perm = await PermissionService(db).create_permission(body)
    return ApiResponse.ok(data=perm, message="创建成功")


# ============================================================
# PUT /permissions/{perm_id} — 全量更新
# ============================================================

@router.put("/{perm_id}", response_model=PermissionBriefResponse, summary="全量更新权限")
async def update_permission(
    perm_id: int,
    body: PermissionUpdate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.UPDATE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    perm = await PermissionService(db, redis_client).update_permission(perm_id, body)
    return ApiResponse.ok(data=perm, message="更新成功")


# ============================================================
# PATCH /permissions/{perm_id} — 部分更新
# ============================================================

@router.patch("/{perm_id}", response_model=PermissionBriefResponse, summary="部分更新权限")
async def patch_permission(
    perm_id: int,
    body: PermissionPatch,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.UPDATE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    perm = await PermissionService(db, redis_client).patch_permission(perm_id, body)
    return ApiResponse.ok(data=perm, message="更新成功")


# ============================================================
# DELETE /permissions/{perm_id} — 删除权限
# ============================================================

@router.delete("/{perm_id}", response_model=ApiResponse, summary="删除权限")
async def delete_permission(
    perm_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.DELETE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    message = await PermissionService(db, redis_client).delete_permission(perm_id)
    return ApiResponse.ok(message=message)

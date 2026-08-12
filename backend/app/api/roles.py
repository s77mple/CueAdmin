"""
角色管理 API — 薄控制器，业务逻辑全部委托给 RoleService。

角色变更的特殊处理：
  修改角色的权限/菜单 → 需要清除所有关联用户的权限缓存
  为什么？因为用户的权限在 Redis 里缓存了 5 分钟，
  角色改了权限，缓存里的数据就过期了，需要主动 invalidate。
"""

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Security

from app.core.database import DbSession
from app.core.dependencies import get_current_user, get_redis
from app.models import User
from app.schemas.response import ApiResponse
from app.schemas.role import (
    RoleCreate, RoleUpdate, RolePatch,
    RoleListResponse, RoleListApiResponse, RoleBriefResponse,
)
from app.services.role_service import RoleService

router = APIRouter()


class RoleScope:
    LIST   = "role:list"
    CREATE = "role:create"
    UPDATE = "role:update"
    DELETE = "role:delete"


# ============================================================
# GET /roles — 角色列表
# ============================================================

@router.get("", response_model=RoleListApiResponse, summary="角色列表")
async def list_roles(
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[RoleScope.LIST])],
):
    roles = await RoleService(db).list_roles()
    data = RoleListResponse(items=roles, total=len(roles))
    return ApiResponse.ok(data=data)


# ============================================================
# POST /roles — 创建角色
# ============================================================

@router.post("", response_model=RoleBriefResponse, status_code=201, summary="创建角色")
async def create_role(
    body: RoleCreate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[RoleScope.CREATE])],
):
    role = await RoleService(db).create_role(body)
    return ApiResponse.ok(data=role, message="创建成功")


# ============================================================
# PUT /roles/{role_id} — 全量更新
# ============================================================

@router.put("/{role_id}", response_model=RoleBriefResponse, summary="全量更新角色")
async def update_role(
    role_id: int,
    body: RoleUpdate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[RoleScope.UPDATE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    role = await RoleService(db, redis_client).update_role(role_id, body)
    return ApiResponse.ok(data=role, message="更新成功")


# ============================================================
# PATCH /roles/{role_id} — 部分更新
# ============================================================

@router.patch("/{role_id}", response_model=RoleBriefResponse, summary="部分更新角色")
async def patch_role(
    role_id: int,
    body: RolePatch,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[RoleScope.UPDATE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    role = await RoleService(db, redis_client).patch_role(role_id, body)
    return ApiResponse.ok(data=role, message="更新成功")


# ============================================================
# DELETE /roles/{role_id} — 删除角色
# ============================================================

@router.delete("/{role_id}", response_model=ApiResponse, summary="删除角色")
async def delete_role(
    role_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[RoleScope.DELETE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    message = await RoleService(db, redis_client).delete_role(role_id)
    return ApiResponse.ok(message=message)

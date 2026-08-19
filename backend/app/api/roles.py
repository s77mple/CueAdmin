"""
角色管理 API — 薄控制器，业务逻辑全部委托给 RoleService。

角色变更的特殊处理：
  修改角色的权限/菜单 → 需要清除所有关联用户的权限缓存
  为什么？因为用户的权限在 Redis 里缓存了 5 分钟，
  角色改了权限，缓存里的数据就过期了，需要主动 invalidate。
"""

from typing import Annotated

from fastapi import APIRouter, Path, Query, Security

from app.core.database import DbSession
from app.core.dependencies import RedisDep, get_current_user
from app.models import User
from app.schemas.response import ApiResponse, PageData
from app.schemas.role import (
    RoleCreate, RoleUpdate,
    RoleItem, RoleBrief,
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

@router.get("", response_model=ApiResponse[PageData[RoleItem]], summary="角色列表")
async def list_roles(
    session: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[RoleScope.LIST])],
    page: Annotated[int, Query(ge=1, description="页码，从 1 开始")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="每页条数，最大 100")] = 100,
) -> ApiResponse[PageData[RoleItem]]:
    result = await RoleService(session).list_roles(page, page_size)
    return ApiResponse.ok(data=result)


# ============================================================
# POST /roles — 创建角色
# ============================================================

@router.post("", response_model=ApiResponse[RoleBrief], status_code=201, summary="创建角色")
async def create_role(
    body: RoleCreate,
    session: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[RoleScope.CREATE])],
) -> ApiResponse[RoleBrief]:
    role = await RoleService(session).create_role(body)
    return ApiResponse.ok(data=role, message="创建成功")


# ============================================================
# PUT /roles/{role_id} — 全量更新
# ============================================================

@router.put("/{role_id}", response_model=ApiResponse[RoleBrief], summary="全量更新角色")
async def update_role(
    role_id: Annotated[int, Path(description="角色 ID")],
    body: RoleUpdate,
    session: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[RoleScope.UPDATE])],
    redis_client: RedisDep,
) -> ApiResponse[RoleBrief]:
    role = await RoleService(session, redis_client).update_role(role_id, body)
    return ApiResponse.ok(data=role, message="更新成功")


# ============================================================
# DELETE /roles/{role_id} — 删除角色
# ============================================================

@router.delete("/{role_id}", response_model=ApiResponse, summary="删除角色")
async def delete_role(
    role_id: Annotated[int, Path(description="角色 ID")],
    session: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[RoleScope.DELETE])],
    redis_client: RedisDep,
) -> ApiResponse:
    message = await RoleService(session, redis_client).delete_role(role_id)
    return ApiResponse.ok(message=message)

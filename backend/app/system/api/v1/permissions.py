"""
权限码管理 API — 薄控制器，业务逻辑全部委托给 PermissionService。
"""

from typing import Annotated

from fastapi import APIRouter, Path, Security

from app.core.dependencies import SessionDep, RedisDep, get_current_user
from app.system.models import User
from app.system.schemas.permission import (
    PermissionCreate, PermissionUpdate,
    PermissionItem, PermissionListResponse, PermissionBrief,
)
from app.core.response import ApiResponse
from app.system.services.permission_service import PermissionService

router = APIRouter(prefix="/permissions", tags=["权限管理"])


class PermissionScope:
    LIST   = "permission:list"
    CREATE = "permission:create"
    UPDATE = "permission:update"
    DELETE = "permission:delete"


# GET /permissions — 权限列表

@router.get("", response_model=ApiResponse[PermissionListResponse], summary="权限列表")
async def list_permissions(
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.LIST])],
) -> ApiResponse[PermissionListResponse]:
    perms = await PermissionService(session).list_permissions()
    data = PermissionListResponse(items=perms, total=len(perms))
    return ApiResponse.ok(data=data)


# GET /permissions/{perm_id} — 权限详情（编辑回显）

@router.get("/{perm_id}", response_model=ApiResponse[PermissionItem], summary="权限详情")
async def get_permission(
    perm_id: Annotated[int, Path(description="权限 ID")],
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.LIST])],
) -> ApiResponse[PermissionItem]:
    perm = await PermissionService(session).get_permission(perm_id)
    return ApiResponse.ok(data=perm)


# POST /permissions — 创建权限

@router.post("", response_model=ApiResponse[PermissionBrief], status_code=201, summary="创建权限")
async def create_permission(
    body: PermissionCreate,
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.CREATE])],
) -> ApiResponse[PermissionBrief]:
    perm = await PermissionService(session).create_permission(body)
    return ApiResponse.ok(data=perm, message="创建成功")


# PUT /permissions/{perm_id} — 全量更新

@router.put("/{perm_id}", response_model=ApiResponse[PermissionBrief], summary="全量更新权限")
async def update_permission(
    perm_id: Annotated[int, Path(description="权限 ID")],
    body: PermissionUpdate,
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.UPDATE])],
    redis_client: RedisDep,
) -> ApiResponse[PermissionBrief]:
    perm = await PermissionService(session, redis_client).update_permission(perm_id, body)
    return ApiResponse.ok(data=perm, message="更新成功")


# DELETE /permissions/{perm_id} — 删除权限

@router.delete("/{perm_id}", response_model=ApiResponse, summary="删除权限")
async def delete_permission(
    perm_id: Annotated[int, Path(description="权限 ID")],
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.DELETE])],
    redis_client: RedisDep,
) -> ApiResponse:
    message = await PermissionService(session, redis_client).delete_permission(perm_id)
    return ApiResponse.ok(message=message)

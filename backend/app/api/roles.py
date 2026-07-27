"""角色管理 API"""

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Security
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import DbSession
from app.core.dependencies import get_current_user, get_redis
from app.core.exceptions import BusinessException, ErrorCode
from app.models import Role, Permission, Menu, User
from app.models.associations import user_roles
from app.schemas.response import ApiResponse
from app.schemas.role import RoleCreate, RoleUpdate, RoleListResponse, RoleListApiResponse, RoleBriefResponse
from app.core.logger import logger

router = APIRouter()


class RoleScope:
    LIST   = "role:list"
    CREATE = "role:create"
    UPDATE = "role:update"
    DELETE = "role:delete"


@router.get("", response_model=RoleListApiResponse, summary="角色列表")
async def list_roles(
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[RoleScope.LIST])],
):
    stmt = (
        select(Role)
        .options(selectinload(Role.permissions), selectinload(Role.menus))
        .order_by(Role.id.asc())
    )
    result = await db.execute(stmt)
    roles = result.scalars().all()
    data = RoleListResponse(
        items=[
            {
                "id": r.id, "code": r.code, "name": r.name,
                "description": r.description, "is_system": r.is_system,
                "permissions": [{"id": p.id, "code": p.code, "name": p.name} for p in r.permissions],
                "menus": [{"id": m.id, "code": m.code, "name": m.name} for m in r.menus],
            }
            for r in roles
        ],
        total=len(roles),
    )
    return ApiResponse.ok(data=data)


@router.post("", response_model=RoleBriefResponse, status_code=201, summary="创建角色")
async def create_role(
    body: RoleCreate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[RoleScope.CREATE])],
):
    if (await db.execute(select(Role).where(Role.code == body.code))).scalars().first():
        raise BusinessException(ErrorCode.ROLE_CODE_EXISTS, "角色编码已存在")
    role = Role(code=body.code, name=body.name, description=body.description)
    if body.permission_codes:
        perms = (await db.execute(
            select(Permission).where(Permission.code.in_(body.permission_codes))
        )).scalars().all()
        if len(perms) != len(body.permission_codes):
            found = {p.code for p in perms}
            logger.warning("创建角色时部分权限 code 无效，已忽略: {}",
                           [c for c in body.permission_codes if c not in found])
        role.permissions = perms
    if body.menu_ids:
        menus = (await db.execute(
            select(Menu).where(Menu.id.in_(body.menu_ids))
        )).scalars().all()
        if len(menus) != len(body.menu_ids):
            logger.warning("创建角色时部分菜单 ID 无效，已忽略")
        role.menus = menus
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return ApiResponse.ok(data=role, message="创建成功")


@router.put("/{role_id}", response_model=RoleBriefResponse, summary="更新角色")
async def update_role(
    role_id: int,
    body: RoleUpdate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[RoleScope.UPDATE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalars().first()
    if not role:
        raise BusinessException(ErrorCode.ROLE_NOT_FOUND, f"角色不存在: {role_id}")
    if body.name is not None:
        role.name = body.name
    if body.description is not None:
        role.description = body.description
    if body.permission_codes is not None:
        perms = (await db.execute(
            select(Permission).where(Permission.code.in_(body.permission_codes))
        )).scalars().all()
        if len(perms) != len(body.permission_codes):
            found = {p.code for p in perms}
            logger.warning("更新角色时部分权限 code 无效，已忽略: {}",
                           [c for c in body.permission_codes if c not in found])
        role.permissions = perms
    if body.menu_ids is not None:
        menus = (await db.execute(
            select(Menu).where(Menu.id.in_(body.menu_ids))
        )).scalars().all()
        if len(menus) != len(body.menu_ids):
            logger.warning("更新角色时部分菜单 ID 无效，已忽略")
        role.menus = menus
    await db.commit()

    if body.permission_codes is not None or body.menu_ids is not None:
        try:
            rows = (await db.execute(
                select(user_roles.c.user_id).where(user_roles.c.role_id == role_id)
            )).all()
            for (uid,) in rows:
                try:
                    await redis_client.delete(f"perm:{uid}")
                except aioredis.RedisError:
                    pass
            logger.info("角色 [{}] 权限/菜单变更，已清除 {} 个用户缓存", role.code, len(rows))
        except Exception as e:
            logger.warning("清除用户缓存失败: {}", e)

    return ApiResponse.ok(data=role, message="更新成功")


@router.delete("/{role_id}", response_model=ApiResponse, summary="删除角色")
async def delete_role(
    role_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[RoleScope.DELETE])],
):
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalars().first()
    if not role:
        raise BusinessException(ErrorCode.ROLE_NOT_FOUND, f"角色不存在: {role_id}")
    if role.is_system:
        raise BusinessException(ErrorCode.ROLE_IS_SYSTEM, "不允许删除系统角色")
    await db.delete(role)
    await db.commit()
    return ApiResponse.ok(message="删除成功")

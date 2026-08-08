"""角色管理 API"""

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Security
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import DbSession
from app.core.dependencies import get_current_user, get_redis
from app.core.exceptions import BusinessException, ErrorCode
from app.models import Role, Permission, Menu, User
from app.models.associations import user_roles
from app.schemas.response import ApiResponse
from app.schemas.role import RoleCreate, RoleUpdate, RolePatch, RoleListResponse, RoleListApiResponse, RoleBriefResponse
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
                "permissions": [{"id": p.id, "code": p.code, "name": p.name, "resource": p.resource} for p in r.permissions],
                "menus": [{"id": m.id, "code": m.code, "name": m.name, "parent_id": m.parent_id} for m in r.menus],
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
            invalid = [c for c in body.permission_codes if c not in found]
            raise BusinessException(ErrorCode.VALIDATION_ERROR, f"权限 code 不存在: {invalid}")
        role.permissions = perms
    if body.menu_ids:
        menus = (await db.execute(
            select(Menu).where(Menu.id.in_(body.menu_ids))
        )).scalars().all()
        if len(menus) != len(body.menu_ids):
            found = {m.id for m in menus}
            invalid = [mid for mid in body.menu_ids if mid not in found]
            raise BusinessException(ErrorCode.VALIDATION_ERROR, f"菜单 ID 不存在: {invalid}")
        role.menus = menus
    db.add(role)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise BusinessException(ErrorCode.ROLE_CODE_EXISTS, "角色编码已存在")
    await db.refresh(role)
    return ApiResponse.ok(data=role, message="创建成功")


async def _resolve_role_relations(
    db: AsyncSession,
    role: Role,
    permission_codes: list[str] | None = None,
    menu_ids: list[int] | None = None,
):
    """校验权限/菜单关联并赋给角色。传入 None 表示不修改该关联。"""
    if permission_codes is not None:
        perms = (await db.execute(
            select(Permission).where(Permission.code.in_(permission_codes))
        )).scalars().all()
        if len(perms) != len(permission_codes):
            found = {p.code for p in perms}
            invalid = [c for c in permission_codes if c not in found]
            raise BusinessException(ErrorCode.VALIDATION_ERROR, f"权限 code 不存在: {invalid}")
        role.permissions = perms

    if menu_ids is not None:
        menus = (await db.execute(
            select(Menu).where(Menu.id.in_(menu_ids))
        )).scalars().all()
        if len(menus) != len(menu_ids):
            found = {m.id for m in menus}
            invalid = [mid for mid in menu_ids if mid not in found]
            raise BusinessException(ErrorCode.VALIDATION_ERROR, f"菜单 ID 不存在: {invalid}")
        role.menus = menus


async def _clear_role_users_cache(db: AsyncSession, redis_client: aioredis.Redis, role_id: int, role_code: str):
    """角色权限/菜单变更后，清除所有关联用户的权限缓存。"""
    try:
        rows = (await db.execute(
            select(user_roles.c.user_id).where(user_roles.c.role_id == role_id)
        )).all()
    except SQLAlchemyError:
        logger.warning("查询角色关联用户失败，跳过缓存清除")
        return
    for (uid,) in rows:
        try:
            await redis_client.delete(f"perm:{uid}")
        except aioredis.RedisError:
            pass
    logger.info("角色 [{}] 权限/菜单变更，已清除 {} 个用户缓存", role_code, len(rows))


@router.put("/{role_id}", response_model=RoleBriefResponse, summary="全量更新角色")
async def update_role(
    role_id: int,
    body: RoleUpdate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[RoleScope.UPDATE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """PUT 全量更新 —— 前端传所有字段（可空字段传 null），直接覆盖"""
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions), selectinload(Role.menus))
        .where(Role.id == role_id)
        .with_for_update()
    )
    role = result.scalars().first()
    if not role:
        raise BusinessException(ErrorCode.ROLE_NOT_FOUND, f"角色不存在: {role_id}")
    if role.is_system:
        raise BusinessException(ErrorCode.ROLE_IS_SYSTEM, "不允许修改系统角色")

    # 全量赋值 + 关联校验
    role.name = body.name
    role.description = body.description
    await _resolve_role_relations(db, role, body.permission_codes, body.menu_ids)
    await db.commit()

    await _clear_role_users_cache(db, redis_client, role_id, role.code)
    return ApiResponse.ok(data=role, message="更新成功")


@router.patch("/{role_id}", response_model=RoleBriefResponse, summary="部分更新角色")
async def patch_role(
    role_id: int,
    body: RolePatch,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[RoleScope.UPDATE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """PATCH 部分更新 —— 仅更新传了的字段"""
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions), selectinload(Role.menus))
        .where(Role.id == role_id)
        .with_for_update()
    )
    role = result.scalars().first()
    if not role:
        raise BusinessException(ErrorCode.ROLE_NOT_FOUND, f"角色不存在: {role_id}")
    if role.is_system:
        raise BusinessException(ErrorCode.ROLE_IS_SYSTEM, "不允许修改系统角色")

    data = body.model_dump(exclude_unset=True)
    relations_changed = False

    if "name" in data:
        if data["name"] is None:
            raise BusinessException(ErrorCode.VALIDATION_ERROR, "name 不能为 null")
        role.name = data["name"]
    if "description" in data:
        role.description = data["description"]
    if "permission_codes" in data:
        await _resolve_role_relations(db, role, permission_codes=data["permission_codes"])
        relations_changed = True
    if "menu_ids" in data:
        await _resolve_role_relations(db, role, menu_ids=data["menu_ids"])
        relations_changed = True

    await db.commit()

    if relations_changed:
        await _clear_role_users_cache(db, redis_client, role_id, role.code)
    return ApiResponse.ok(data=role, message="更新成功")


@router.delete("/{role_id}", response_model=ApiResponse, summary="删除角色")
async def delete_role(
    role_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[RoleScope.DELETE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    result = await db.execute(
        select(Role).where(Role.id == role_id).with_for_update()
    )
    role = result.scalars().first()
    if not role:
        raise BusinessException(ErrorCode.ROLE_NOT_FOUND, f"角色不存在: {role_id}")
    if role.is_system:
        raise BusinessException(ErrorCode.ROLE_IS_SYSTEM, "不允许删除系统角色")
    # 删除前查出关联用户，用于清除缓存
    try:
        rows = (await db.execute(
            select(user_roles.c.user_id).where(user_roles.c.role_id == role_id)
        )).all()
    except SQLAlchemyError:
        rows = []
        logger.warning("查询角色关联用户失败，跳过缓存清除")
    await db.delete(role)
    await db.commit()
    # 清除所有关联用户的权限缓存
    for (uid,) in rows:
        try:
            await redis_client.delete(f"perm:{uid}")
        except aioredis.RedisError:
            pass
    if rows:
        logger.info("角色 [{}] 已删除，清除 {} 个用户缓存", role.code, len(rows))
    return ApiResponse.ok(message="删除成功")

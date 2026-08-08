"""用户管理 API"""

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.database import DbSession
from app.core.dependencies import get_current_user, get_redis
from app.core.exceptions import BusinessException, ErrorCode
from app.core.paginate import paginate
from app.core.security import hash_password
from app.models import User, Role, Department
from app.schemas.response import ApiResponse
from app.schemas.user import UserCreate, UserUpdate, UserPatch, UserRead, UserReadResponse, UserListResponse

router = APIRouter()


class UserScope:
    LIST   = "user:list"
    CREATE = "user:create"
    UPDATE = "user:update"
    DELETE = "user:delete"


@router.get("", response_model=UserListResponse, summary="用户列表")
async def list_users(
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.LIST])],
    role_id: int | None = Query(None),
    is_active: bool | None = Query(None, description="筛选启用/禁用状态，不传则查全部"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = select(User).options(selectinload(User.roles), selectinload(User.department))
    if role_id is not None:
        stmt = stmt.join(User.roles).where(Role.id == role_id)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    stmt = stmt.order_by(User.id.asc())
    result = await paginate(db, stmt, page, page_size)
    return ApiResponse.ok(data=result)


@router.get("/{user_id}", response_model=UserReadResponse, summary="用户详情")
async def get_user(
    user_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.LIST])],
):
    stmt = select(User).options(selectinload(User.roles), selectinload(User.department)).where(User.id == user_id)
    result = await db.execute(stmt)
    target = result.scalars().first()
    if not target:
        raise BusinessException(ErrorCode.USER_NOT_FOUND, f"用户不存在: {user_id}")
    return ApiResponse.ok(data=target)


@router.post("", response_model=UserReadResponse, status_code=201, summary="创建用户")
async def create_user(
    body: UserCreate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.CREATE])],
):
    if (await db.execute(select(User).where(User.username == body.username))).scalars().first():
        raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")
    # 验证部门存在
    if body.department_id is not None:
        dept = (await db.execute(select(Department).where(Department.id == body.department_id))).scalars().first()
        if not dept:
            raise BusinessException(ErrorCode.VALIDATION_ERROR, f"部门不存在: {body.department_id}")
    new_user = User(
        username=body.username, password_hash=await hash_password(body.password),
        display_name=body.display_name, phone=body.phone,
        department_id=body.department_id,
    )
    if body.role_ids:
        roles = (await db.execute(
            select(Role).where(Role.id.in_(body.role_ids))
        )).scalars().all()
        if len(roles) != len(body.role_ids):
            found = {r.id for r in roles}
            invalid = [rid for rid in body.role_ids if rid not in found]
            raise BusinessException(ErrorCode.VALIDATION_ERROR, f"角色 ID 不存在: {invalid}")
        new_user.roles = roles
    db.add(new_user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")
    await db.refresh(new_user)
    return ApiResponse.ok(data=new_user, message="创建成功")


async def _validate_username_unique(db: DbSession, username: str, exclude_user_id: int | None = None):
    stmt = select(User).where(User.username == username)
    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)
    if (await db.execute(stmt)).scalars().first():
        raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")


async def _resolve_user_dept(db: DbSession, department_id: int | None):
    if department_id is not None:
        dept = (await db.execute(select(Department).where(Department.id == department_id))).scalars().first()
        if not dept:
            raise BusinessException(ErrorCode.VALIDATION_ERROR, f"部门不存在: {department_id}")


async def _resolve_user_roles(db: DbSession, target: User, role_ids: list[int]):
    """验证角色 ID 存在并赋值，同时防止移除最后一个管理员的 admin 角色。"""
    roles = (await db.execute(
        select(Role).where(Role.id.in_(role_ids))
    )).scalars().all()
    if len(roles) != len(role_ids):
        found = {r.id for r in roles}
        invalid = [rid for rid in role_ids if rid not in found]
        raise BusinessException(ErrorCode.VALIDATION_ERROR, f"角色 ID 不存在: {invalid}")
    admin_role = next((r for r in roles if r.code == "admin"), None)
    had_admin = any(r.code == "admin" for r in target.roles)
    will_lose_admin = had_admin and admin_role is None
    if will_lose_admin:
        admin_count = (await db.execute(
            select(User).join(User.roles).where(
                Role.code == "admin", User.is_active == True
            ).with_for_update()
        )).scalars().all()
        if len(admin_count) <= 1:
            raise BusinessException(ErrorCode.CONFLICT, "不允许移除最后一个管理员的 admin 角色")
    target.roles = roles


@router.put("/{user_id}", response_model=UserReadResponse, summary="全量更新用户")
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.UPDATE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """PUT 全量更新 —— 除 password 外所有字段必传，可空字段传 null"""
    # 行级锁：防止并发修改同一用户的角色（需 eager load roles 防 async lazy load）
    result = await db.execute(
        select(User).options(selectinload(User.roles), selectinload(User.department)).where(User.id == user_id).with_for_update()
    )
    target = result.scalars().first()
    if not target:
        raise BusinessException(ErrorCode.USER_NOT_FOUND, f"用户不存在: {user_id}")

    # 全量赋值
    if body.username != target.username:
        await _validate_username_unique(db, body.username)
        target.username = body.username
    if body.password:
        target.password_hash = await hash_password(body.password)
    target.display_name = body.display_name
    target.phone = body.phone
    if not body.is_active:
        if target.username == "admin":
            raise BusinessException(ErrorCode.USER_CANNOT_DISABLE_SUPERADMIN, "不允许禁用超级管理员")
        # 防止禁用最后一个活跃管理员
        if any(r.code == "admin" for r in target.roles):
            admin_count = (await db.execute(
                select(User).join(User.roles).where(
                    Role.code == "admin", User.is_active == True
                ).with_for_update()
            )).scalars().all()
            if len(admin_count) <= 1:
                raise BusinessException(ErrorCode.CONFLICT, "不允许禁用最后一个管理员")
    target.is_active = body.is_active
    await _resolve_user_dept(db, body.department_id)
    target.department_id = body.department_id
    old_role_ids = {r.id for r in target.roles}
    await _resolve_user_roles(db, target, body.role_ids)
    roles_changed = {r.id for r in target.roles} != old_role_ids

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")
    await db.refresh(target)

    if roles_changed:
        try:
            await redis_client.delete(f"perm:{user_id}")
        except aioredis.RedisError:
            pass

    return ApiResponse.ok(data=target, message="更新成功")


@router.patch("/{user_id}", response_model=UserReadResponse, summary="部分更新用户")
async def patch_user(
    user_id: int,
    body: UserPatch,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.UPDATE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """PATCH 部分更新 —— 仅更新传了的字段"""
    result = await db.execute(
        select(User).options(selectinload(User.roles), selectinload(User.department)).where(User.id == user_id).with_for_update()
    )
    target = result.scalars().first()
    if not target:
        raise BusinessException(ErrorCode.USER_NOT_FOUND, f"用户不存在: {user_id}")

    data = body.model_dump(exclude_unset=True)

    if "username" in data:
        if data["username"] is None:
            raise BusinessException(ErrorCode.VALIDATION_ERROR, "username 不能为 null")
        if data["username"] != target.username:
            await _validate_username_unique(db, data["username"])
            target.username = data["username"]
    if "password" in data and data["password"]:
        target.password_hash = await hash_password(data["password"])
    if "display_name" in data:
        if data["display_name"] is None:
            raise BusinessException(ErrorCode.VALIDATION_ERROR, "display_name 不能为 null")
        target.display_name = data["display_name"]
    if "phone" in data:
        target.phone = data["phone"]
    if "is_active" in data:
        if not data["is_active"]:
            if target.username == "admin":
                raise BusinessException(ErrorCode.USER_CANNOT_DISABLE_SUPERADMIN, "不允许禁用超级管理员")
            if any(r.code == "admin" for r in target.roles):
                admin_count = (await db.execute(
                    select(User).join(User.roles).where(
                        Role.code == "admin", User.is_active == True
                    ).with_for_update()
                )).scalars().all()
                if len(admin_count) <= 1:
                    raise BusinessException(ErrorCode.CONFLICT, "不允许禁用最后一个管理员")
        target.is_active = data["is_active"]
    if "department_id" in data:
        await _resolve_user_dept(db, data["department_id"])
        target.department_id = data["department_id"]
    if "role_ids" in data:
        await _resolve_user_roles(db, target, data["role_ids"])

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")
    await db.refresh(target)

    if "role_ids" in data:
        try:
            await redis_client.delete(f"perm:{user_id}")
        except aioredis.RedisError:
            pass

    return ApiResponse.ok(data=target, message="更新成功")


@router.delete("/{user_id}", response_model=ApiResponse, summary="禁用/删除用户")
async def delete_user(
    user_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.DELETE])],
    hard: bool = Query(False, description="true=彻底删除（仅限已禁用的用户），默认 false=软禁用"),
    redis_client: aioredis.Redis = Depends(get_redis),
):
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id).with_for_update()
    )
    target = result.scalars().first()
    if not target:
        raise BusinessException(ErrorCode.USER_NOT_FOUND, f"用户不存在: {user_id}")
    if user.id == user_id:
        raise BusinessException(ErrorCode.CONFLICT, "不允许操作自己的账号")
    if target.username == "admin":
        raise BusinessException(ErrorCode.USER_CANNOT_DISABLE_SUPERADMIN, "不允许操作超级管理员")

    if hard:
        # 硬删除：仅允许删除已禁用的用户
        if target.is_active:
            raise BusinessException(ErrorCode.CONFLICT, "不允许彻底删除启用状态的用户，请先禁用")
        # 防御：如果用户拥有 admin 角色，确保还有其他活跃管理员
        if any(r.code == "admin" for r in target.roles):
            admin_count = (await db.execute(
                select(User).join(User.roles).where(
                    Role.code == "admin", User.is_active == True
                ).with_for_update()
            )).scalars().all()
            if len(admin_count) < 1:
                raise BusinessException(ErrorCode.CONFLICT, "不允许删除最后一个拥有管理员角色的用户")
        # 清除权限缓存
        try:
            await redis_client.delete(f"perm:{user_id}")
        except aioredis.RedisError:
            pass
        await db.delete(target)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise BusinessException(ErrorCode.CONFLICT, "删除失败：存在关联数据")
        return ApiResponse.ok(message="已彻底删除")
    else:
        # 软删除：禁用用户
        if not target.is_active:
            raise BusinessException(ErrorCode.CONFLICT, "该用户已被禁用")
        # 防止禁用最后一个活跃管理员
        if any(r.code == "admin" for r in target.roles):
            admin_count = (await db.execute(
                select(User).join(User.roles).where(
                    Role.code == "admin", User.is_active == True
                ).with_for_update()
            )).scalars().all()
            if len(admin_count) <= 1:
                raise BusinessException(ErrorCode.CONFLICT, "不允许禁用最后一个管理员")
        target.is_active = False
        await db.commit()
        return ApiResponse.ok(message="已禁用")

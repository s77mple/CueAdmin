"""用户管理 API"""

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import DbSession
from app.core.dependencies import get_current_user, get_redis
from app.core.exceptions import BusinessException, ErrorCode
from app.core.paginate import paginate
from app.core.security import hash_password
from app.models import User, Role
from app.schemas.response import ApiResponse
from app.schemas.user import UserCreate, UserUpdate, UserRead, UserReadResponse, UserListResponse

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
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = select(User).options(selectinload(User.roles))
    if role_id is not None:
        stmt = stmt.join(User.roles).where(Role.id == role_id)
    stmt = stmt.order_by(User.id.asc())
    result = await paginate(db, stmt, page, page_size)
    return ApiResponse.ok(data=result)


@router.get("/{user_id}", response_model=UserReadResponse, summary="用户详情")
async def get_user(
    user_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.LIST])],
):
    stmt = select(User).options(selectinload(User.roles)).where(User.id == user_id)
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
    new_user = User(
        username=body.username, password_hash=await hash_password(body.password),
        display_name=body.display_name, phone=body.phone,
    )
    if body.role_ids:
        new_user.roles = (await db.execute(
            select(Role).where(Role.id.in_(body.role_ids))
        )).scalars().all()
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return ApiResponse.ok(data=new_user, message="创建成功")


@router.put("/{user_id}", response_model=UserReadResponse, summary="更新用户")
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.UPDATE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalars().first()
    if not target:
        raise BusinessException(ErrorCode.USER_NOT_FOUND, f"用户不存在: {user_id}")
    if body.username is not None and body.username != target.username:
        if (await db.execute(select(User).where(User.username == body.username))).scalars().first():
            raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")
        target.username = body.username
    if body.password is not None:
        target.password_hash = await hash_password(body.password)
    if body.display_name is not None:
        target.display_name = body.display_name
    if body.phone is not None:
        target.phone = body.phone
    if body.is_active is not None:
        if target.username == "admin" and not body.is_active:
            raise BusinessException(ErrorCode.USER_CANNOT_DISABLE_SUPERADMIN, "不允许禁用超级管理员")
        target.is_active = body.is_active
    if body.role_ids is not None:
        target.roles = (await db.execute(
            select(Role).where(Role.id.in_(body.role_ids))
        )).scalars().all()
    await db.commit()
    await db.refresh(target)

    if body.role_ids is not None:
        try:
            await redis_client.delete(f"perm:{user_id}")
        except aioredis.RedisError:
            pass

    return ApiResponse.ok(data=target, message="更新成功")


@router.delete("/{user_id}", response_model=ApiResponse, summary="禁用用户")
async def delete_user(
    user_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.DELETE])],
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalars().first()
    if not target:
        raise BusinessException(ErrorCode.USER_NOT_FOUND, f"用户不存在: {user_id}")
    if target.username == "admin":
        raise BusinessException(ErrorCode.USER_CANNOT_DISABLE_SUPERADMIN, "不允许禁用超级管理员")
    target.is_active = False
    await db.commit()
    return ApiResponse.ok(message="已禁用")

"""用户管理 API"""

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import DbSession
from app.core.dependencies import get_current_user, get_redis
from app.core.security import hash_password
from app.models import User, Role
from app.schemas.user import UserCreate, UserUpdate, UserRead
from app.core.exceptions import NotFoundException, ConflictException

router = APIRouter()


# ---- 权限码常量 ----
class UserScope:
    LIST   = "user:list"
    CREATE = "user:create"
    UPDATE = "user:update"
    DELETE = "user:delete"


@router.get("", summary="用户列表")
async def list_users(
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.LIST])],
    role_id: int | None = Query(None),
    skip: int = Query(0),
    limit: int = Query(20),
):
    query = select(User)
    if role_id is not None:
        query = query.join(User.roles).where(Role.id == role_id)

    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_stmt)).scalar()

    query = query.options(selectinload(User.roles)).order_by(User.id.asc()).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    page = skip // limit + 1 if limit > 0 else 1
    return {
        "items": [
            {
                "id": u.id, "username": u.username, "display_name": u.display_name,
                "phone": u.phone, "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "updated_at": u.updated_at.isoformat() if u.updated_at else None,
                "role_ids": [r.id for r in u.roles],
                "role_names": "、".join([r.name for r in u.roles]) if u.roles else "",
            }
            for u in users
        ],
        "total": total, "page": page, "page_size": limit,
        "has_more": page * limit < total,
    }


@router.get("/{user_id}", summary="用户详情")
async def get_user(
    user_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.LIST])],
):
    stmt = select(User).options(selectinload(User.roles)).where(User.id == user_id)
    result = await db.execute(stmt)
    target = result.scalars().first()
    if not target:
        raise NotFoundException("User", user_id)
    return {
        "id": target.id, "username": target.username, "display_name": target.display_name,
        "phone": target.phone, "is_active": target.is_active,
        "created_at": target.created_at.isoformat() if target.created_at else None,
        "updated_at": target.updated_at.isoformat() if target.updated_at else None,
        "role_ids": [r.id for r in target.roles],
    }


@router.post("", response_model=UserRead, status_code=201, summary="创建用户")
async def create_user(
    body: UserCreate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.CREATE])],
):
    if (await db.execute(select(User).where(User.username == body.username))).scalars().first():
        raise ConflictException("用户名已存在")
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
    return new_user


@router.put("/{user_id}", response_model=UserRead, summary="更新用户")
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
        raise NotFoundException("User", user_id)
    if body.username is not None and body.username != target.username:
        if (await db.execute(select(User).where(User.username == body.username))).scalars().first():
            raise ConflictException("用户名已存在")
        target.username = body.username
    if body.password is not None:
        target.password_hash = await hash_password(body.password)
    if body.display_name is not None:
        target.display_name = body.display_name
    if body.phone is not None:
        target.phone = body.phone
    if body.is_active is not None:
        if target.username == "admin" and not body.is_active:
            raise ConflictException("不允许禁用超级管理员")
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

    return target


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.DELETE])],
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalars().first()
    if not target:
        raise NotFoundException("User", user_id)
    if target.username == "admin":
        raise ConflictException("不允许禁用超级管理员")
    target.is_active = False
    await db.commit()
    return {"message": "已禁用"}

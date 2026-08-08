"""
权限码管理 API — 细粒度操作权限的 CRUD。

权限的特殊处理：
  - 权限 code 修改后 → 清除所有关联用户的权限缓存
    因为缓存的 key 是 perm:{user_id}，value 是 code 集合，
    code 改了意味着缓存里旧 code 失效。
  - 删除权限 → 删前清除缓存（删后关联表 CASCADE 查不到关联角色）
"""

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Security
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.database import DbSession
from app.core.dependencies import get_current_user, get_redis
from app.core.exceptions import BusinessException, ErrorCode
from app.models import Permission, User
from app.models.associations import user_roles, role_permissions
from app.schemas.permission import PermissionCreate, PermissionUpdate, PermissionPatch, PermissionListResponse, PermissionListApiResponse, PermissionBriefResponse
from app.schemas.response import ApiResponse
from app.core.logger import logger

router = APIRouter()


# ============================================================
# 1. 辅助函数 — 清除关联用户的权限缓存
# ============================================================

async def _clear_perm_cache(db: DbSession, redis_client: aioredis.Redis, perm_id: int):
    """#1 权限变更后，找出所有拥有该权限的用户，清除他们的 Redis 缓存。

    查询路径：
      perm_id → role_permissions 表 → role_id → user_roles 表 → user_id
      这是两次 JOIN，DISTINCT 去重。
    """
    try:
        rows = (await db.execute(
            select(user_roles.c.user_id)
            .join(role_permissions, role_permissions.c.role_id == user_roles.c.role_id)
            .where(role_permissions.c.permission_id == perm_id)
            .distinct()
        )).all()
    except SQLAlchemyError:
        logger.warning("查询权限关联用户失败，跳过缓存清除")
        return
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


# ============================================================
# 2. GET /permissions — 权限列表
# ============================================================

@router.get("", response_model=PermissionListApiResponse, summary="权限列表")
async def list_permissions(
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.LIST])],
):
    """#2 按 resource + action 排序，方便前端展示分组。"""
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


# ============================================================
# 3. POST /permissions — 创建权限
# ============================================================

@router.post("", response_model=PermissionBriefResponse, status_code=201, summary="创建权限")
async def create_permission(
    body: PermissionCreate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.CREATE])],
):
    """#3 创建权限 — 双重唯一性保护。"""
    if (await db.execute(select(Permission).where(Permission.code == body.code))).scalars().first():
        raise BusinessException(ErrorCode.PERM_CODE_EXISTS, "权限编码已存在")
    perm = Permission(
        code=body.code, name=body.name,
        resource=body.resource, action=body.action,
        description=body.description,
    )
    db.add(perm)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise BusinessException(ErrorCode.PERM_CODE_EXISTS, "权限编码已存在")
    await db.refresh(perm)
    return ApiResponse.ok(data=perm, message="创建成功")


# ============================================================
# 4. PUT /permissions/{perm_id} — 全量更新
# ============================================================

@router.put("/{perm_id}", response_model=PermissionBriefResponse, summary="全量更新权限")
async def update_permission(
    perm_id: int,
    body: PermissionUpdate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.UPDATE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """#4 PUT 全量更新 — code 改了需要清缓存。"""
    result = await db.execute(
        select(Permission).where(Permission.id == perm_id).with_for_update()
    )
    perm = result.scalars().first()
    if not perm:
        raise BusinessException(ErrorCode.PERM_NOT_FOUND, f"权限不存在: {perm_id}")

    # code 变更 → 缓存需要失效（缓存里存的是旧 code）
    code_changed = False
    if body.code != perm.code:
        if (await db.execute(select(Permission).where(Permission.code == body.code))).scalars().first():
            raise BusinessException(ErrorCode.PERM_CODE_EXISTS, "权限编码已存在")
        perm.code = body.code
        code_changed = True

    # 全量覆盖
    perm.name = body.name
    perm.resource = body.resource
    perm.action = body.action
    perm.description = body.description

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise BusinessException(ErrorCode.PERM_CODE_EXISTS, "权限编码已存在")
    if code_changed:
        await _clear_perm_cache(db, redis_client, perm_id)
    return ApiResponse.ok(data=perm, message="更新成功")


# ============================================================
# 5. PATCH /permissions/{perm_id} — 部分更新
# ============================================================

@router.patch("/{perm_id}", response_model=PermissionBriefResponse, summary="部分更新权限")
async def patch_permission(
    perm_id: int,
    body: PermissionPatch,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.UPDATE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """#5 PATCH 部分更新 — 必填字段（code/name/resource/action）不允许传 null。"""
    result = await db.execute(
        select(Permission).where(Permission.id == perm_id).with_for_update()
    )
    perm = result.scalars().first()
    if not perm:
        raise BusinessException(ErrorCode.PERM_NOT_FOUND, f"权限不存在: {perm_id}")

    data = body.model_dump(exclude_unset=True)
    code_changed = False

    if "code" in data:
        if data["code"] is None:
            raise BusinessException(ErrorCode.VALIDATION_ERROR, "code 不能为 null")
        if data["code"] != perm.code:
            if (await db.execute(select(Permission).where(Permission.code == data["code"]))).scalars().first():
                raise BusinessException(ErrorCode.PERM_CODE_EXISTS, "权限编码已存在")
            perm.code = data["code"]
            code_changed = True
    if "name" in data:
        if data["name"] is None:
            raise BusinessException(ErrorCode.VALIDATION_ERROR, "name 不能为 null")
        perm.name = data["name"]
    if "resource" in data:
        if data["resource"] is None:
            raise BusinessException(ErrorCode.VALIDATION_ERROR, "resource 不能为 null")
        perm.resource = data["resource"]
    if "action" in data:
        if data["action"] is None:
            raise BusinessException(ErrorCode.VALIDATION_ERROR, "action 不能为 null")
        perm.action = data["action"]
    if "description" in data:
        perm.description = data["description"]

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise BusinessException(ErrorCode.PERM_CODE_EXISTS, "权限编码已存在")
    if code_changed:
        await _clear_perm_cache(db, redis_client, perm_id)
    return ApiResponse.ok(data=perm, message="更新成功")


# ============================================================
# 6. DELETE /permissions/{perm_id} — 删除权限
# ============================================================

@router.delete("/{perm_id}", response_model=ApiResponse, summary="删除权限")
async def delete_permission(
    perm_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[PermissionScope.DELETE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """#6 删除权限 — 删前清除缓存（关键！）。

    为什么删前清除？因为删除后 role_permissions 关联表的记录会 CASCADE 删除，
    再查 role_permissions WHERE permission_id=X 就查不到关联角色了。
    """
    result = await db.execute(
        select(Permission).where(Permission.id == perm_id).with_for_update()
    )
    perm = result.scalars().first()
    if not perm:
        raise BusinessException(ErrorCode.PERM_NOT_FOUND, f"权限不存在: {perm_id}")

    await _clear_perm_cache(db, redis_client, perm_id)  # 先清缓存
    await db.delete(perm)                                # 再删记录
    await db.commit()
    return ApiResponse.ok(message="删除成功")

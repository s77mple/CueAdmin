"""
用户管理 API — 薄控制器，业务逻辑全部委托给 UserService。

每个端点职责：
  1. 提取请求参数
  2. 注入依赖（DB、Redis、当前用户）
  3. 调 UserService 方法
  4. 包装 ApiResponse 返回

安全设计要点：
  - 行级锁 .with_for_update()：防止并发修改同一行
  - TOCTOU 防护：唯一性校验 + IntegrityError 双保险
  - admin 保护：不能禁用/删除最后一个管理员
  - 不能操作自己：防止把自己锁在外面
  - 权限缓存主动失效：角色变更 → 删除 Redis perm:{uid}
"""

from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Path, Query, Security

from app.core.database import DbSession
from app.core.dependencies import get_current_user, get_redis
from app.core.exceptions import BusinessException, ErrorCode
from app.models import User
from app.schemas.response import ApiResponse
from app.schemas.user import UserCreate, UserUpdate, UserPatch, UserReadResponse, UserListResponse
from app.services.user_service import UserService

router = APIRouter()


class UserScope:
    LIST   = "user:list"
    CREATE = "user:create"
    UPDATE = "user:update"
    DELETE = "user:delete"


# ============================================================
# GET /users — 用户列表
# ============================================================

@router.get("", response_model=UserListResponse, summary="用户列表")
async def list_users(
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.LIST])],
    role_id: int | None = Query(None, description="按角色 ID 筛选"),
    is_active: bool | None = Query(None, description="筛选启用/禁用状态，不传则查全部"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数，最大 100"),
):
    svc = UserService(db)
    result = await svc.list_users(role_id=role_id, is_active=is_active, page=page, page_size=page_size)
    return ApiResponse.ok(data=result)


# ============================================================
# POST /users — 创建用户
# ============================================================

@router.post("", response_model=UserReadResponse, status_code=201, summary="创建用户")
async def create_user(
    body: UserCreate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.CREATE])],
):
    new_user = await UserService(db).create_user(body)
    return ApiResponse.ok(data=new_user, message="创建成功")


# ============================================================
# PUT /users/{user_id} — 全量更新
# ============================================================

@router.put("/{user_id}", response_model=UserReadResponse, summary="全量更新用户")
async def update_user(
    user_id: Annotated[int, Path(description="用户 ID")],
    body: UserUpdate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.UPDATE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    target = await UserService(db, redis_client).update_user(user_id, body)
    return ApiResponse.ok(data=target, message="更新成功")


# ============================================================
# PATCH /users/{user_id} — 部分更新
# ============================================================

@router.patch("/{user_id}", response_model=UserReadResponse, summary="部分更新用户")
async def patch_user(
    user_id: Annotated[int, Path(description="用户 ID")],
    body: UserPatch,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.UPDATE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    target = await UserService(db, redis_client).patch_user(user_id, body)
    return ApiResponse.ok(data=target, message="更新成功")


# ============================================================
# DELETE /users/{user_id} — 软禁用 / 硬删除
# ============================================================

@router.delete("/{user_id}", response_model=ApiResponse, summary="禁用/删除用户")
async def delete_user(
    user_id: Annotated[int, Path(description="用户 ID")],
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.DELETE])],
    hard: bool = Query(False, description="true=彻底删除（仅限已禁用的用户），默认 false=软禁用"),
    redis_client: aioredis.Redis = Depends(get_redis),
):
    message = await UserService(db, redis_client).delete_user(user_id, user.id, hard=hard)
    return ApiResponse.ok(message=message)

"""
用户管理 API — 最完整的 CRUD 示例，展示本项目 API 的设计模式。

这个文件的模式适用于所有管理后台的 CRUD 接口：

  GET    /users           → 列表（分页 + 角色筛选 + 状态筛选）
  GET    /users/{id}      → 详情（预加载角色和部门）
  POST   /users           → 创建（校验唯一性 + 外键存在性 + IntegrityError 兜底）
  PUT    /users/{id}      → 全量更新（所有字段必传，覆盖写入）
  PATCH  /users/{id}      → 部分更新（只传要改的字段）
  DELETE /users/{id}      → 软禁用（默认）+ 硬删除（?hard=true）

安全设计要点：
  - 行级锁 .with_for_update()：防止并发修改同一行
  - TOCTOU 防护：唯一性校验 + IntegrityError 双保险
  - admin 保护：不能禁用/删除最后一个管理员
  - 不能操作自己：防止把自己锁在外面
  - 权限缓存主动失效：角色变更 → 删除 Redis perm:{uid}

前端对应的操作流程：
  列表页 → loadUsers() → GET /users → 表格渲染
  创建弹窗 → 填表单 → POST /users → 刷新列表
  编辑弹窗 → PUT /users/{id}（全量） 或 PATCH /users/{id}（单独改状态）
  删除按钮 → DELETE /users/{id} → 软禁用
  彻底删除 → DELETE /users/{id}?hard=true（仅已禁用用户可用）
"""

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


# ============================================================
# 1. 权限 scope 定义 — 每个操作需要的权限码
# ============================================================
# 前端用 v-perms="['user:list']" 控制按钮显隐
# 后端用 Security(get_current_user, scopes=[UserScope.LIST]) 强制校验

class UserScope:
    LIST   = "user:list"
    CREATE = "user:create"
    UPDATE = "user:update"
    DELETE = "user:delete"


# ============================================================
# 2. GET /users — 用户列表（分页 + 角色筛选 + 状态筛选）
# ============================================================

@router.get("", response_model=UserListResponse, summary="用户列表")
async def list_users(
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.LIST])],
    role_id: int | None = Query(None),                        # ?role_id=1 → 按角色筛选
    is_active: bool | None = Query(None, description="筛选启用/禁用状态，不传则查全部"),
    page: int = Query(1, ge=1),                               # 页码，从 1 开始
    page_size: int = Query(20, ge=1, le=100),                 # 每页最多 100 条
):
    """#2 分页列表。

    前端表格请求：GET /api/v1/users?page=1&page_size=20&is_active=true&role_id=1
    后端返回：{ code: 0, data: { items: [...], total: 50, page: 1, page_size: 20, has_more: true } }
    """
    # 预加载角色和部门（一次 IN 查询额外带出关联数据，避免 N+1）
    stmt = select(User).options(selectinload(User.roles), selectinload(User.department))

    # 可选筛选条件
    if role_id is not None:
        stmt = stmt.join(User.roles).where(Role.id == role_id)  # JOIN 筛选指定角色的用户
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)           # 筛选启用/禁用

    stmt = stmt.order_by(User.id.asc())

    # paginate() 自动做 COUNT + 分页 + DISTINCT（防止 JOIN 重复行）
    result = await paginate(db, stmt, page, page_size)
    return ApiResponse.ok(data=result)


# ============================================================
# 3. GET /users/{user_id} — 用户详情
# ============================================================

@router.get("/{user_id}", response_model=UserReadResponse, summary="用户详情")
async def get_user(
    user_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.LIST])],
):
    """#3 单个用户详情。前端编辑弹窗打开时调用。"""
    stmt = select(User).options(selectinload(User.roles), selectinload(User.department)).where(User.id == user_id)
    result = await db.execute(stmt)
    target = result.scalars().first()
    if not target:
        raise BusinessException(ErrorCode.USER_NOT_FOUND, f"用户不存在: {user_id}")
    return ApiResponse.ok(data=target)


# ============================================================
# 4. POST /users — 创建用户
# ============================================================

@router.post("", response_model=UserReadResponse, status_code=201, summary="创建用户")
async def create_user(
    body: UserCreate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.CREATE])],
):
    """#4 创建用户。

    双重唯一性校验：
      a. 先 SELECT 检查（99.9% 的情况被挡在这）
      b. IntegrityError 兜底（并发下 SELECT 和 INSERT 之间另一个请求抢先插入）
    """
    # a. 应用层唯一性检查
    if (await db.execute(select(User).where(User.username == body.username))).scalars().first():
        raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")

    # 验证部门存在（外键约束，提前友好报错）
    if body.department_id is not None:
        dept = (await db.execute(select(Department).where(Department.id == body.department_id))).scalars().first()
        if not dept:
            raise BusinessException(ErrorCode.VALIDATION_ERROR, f"部门不存在: {body.department_id}")

    # 构建 ORM 对象
    new_user = User(
        username=body.username,
        password_hash=await hash_password(body.password),  # bcrypt 哈希（异步，f放线程池）
        display_name=body.display_name,
        phone=body.phone,
        department_id=body.department_id,
    )

    # 验证角色存在 + 赋值
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

    # b. 数据库层唯一性兜底（TOCTOU 防护）
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")

    await db.refresh(new_user)  # 刷新拿到数据库生成的 id、created_at 等
    return ApiResponse.ok(data=new_user, message="创建成功")


# ============================================================
# 5. 辅助函数 — 减少重复代码
# ============================================================

async def _validate_username_unique(db: DbSession, username: str, exclude_user_id: int | None = None):
    """#5a 检查用户名唯一（编辑时排除自己）。"""
    stmt = select(User).where(User.username == username)
    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)  # 改回原来的用户名不算冲突
    if (await db.execute(stmt)).scalars().first():
        raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")


async def _resolve_user_dept(db: DbSession, department_id: int | None):
    """#5b 校验部门存在（null 表示清空部门）。"""
    if department_id is not None:
        dept = (await db.execute(select(Department).where(Department.id == department_id))).scalars().first()
        if not dept:
            raise BusinessException(ErrorCode.VALIDATION_ERROR, f"部门不存在: {department_id}")


async def _resolve_user_roles(db: DbSession, target: User, role_ids: list[int]):
    """#5c 验证角色 ID 存在并赋值。

    额外包含"最后一个管理员保护"：
    如果当前用户在移除自己的 admin 角色，且这是系统中唯一的活跃管理员 →
    不允许操作，防止系统变成无管理状态。
    """
    # 验证所有 role_id 存在
    roles = (await db.execute(
        select(Role).where(Role.id.in_(role_ids))
    )).scalars().all()
    if len(roles) != len(role_ids):
        found = {r.id for r in roles}
        invalid = [rid for rid in role_ids if rid not in found]
        raise BusinessException(ErrorCode.VALIDATION_ERROR, f"角色 ID 不存在: {invalid}")

    # 检查是否在移除最后一个管理员的 admin 角色
    admin_role = next((r for r in roles if r.code == "admin"), None)
    had_admin = any(r.code == "admin" for r in target.roles)
    will_lose_admin = had_admin and admin_role is None

    if will_lose_admin:
        # 锁住所有活跃 admin 用户行，原子检查（加了行级锁防并发）
        admin_count = (await db.execute(
            select(User).join(User.roles).where(
                Role.code == "admin", User.is_active == True
            ).with_for_update()
        )).scalars().all()
        if len(admin_count) <= 1:
            raise BusinessException(ErrorCode.CONFLICT, "不允许移除最后一个管理员的 admin 角色")

    target.roles = roles


# ============================================================
# 6. PUT /users/{user_id} — 全量更新（替换所有字段）
# ============================================================

@router.put("/{user_id}", response_model=UserReadResponse, summary="全量更新用户")
async def update_user(
    user_id: int,
    body: UserUpdate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.UPDATE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """#6 PUT 全量更新。

    RESTful 规范：
      PUT = 全量替换，前端必须传所有字段（password 除外）
      PATCH = 部分更新，只传要改的字段

    前端编辑弹窗点"保存"时调用此接口。
    所有字段（display_name, phone, is_active, role_ids, department_id）全覆盖写入。
    """
    # 行级锁 + 预加载：防止并发修改同一用户的角色
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles), selectinload(User.department))
        .where(User.id == user_id)
        .with_for_update()  # SELECT ... FOR UPDATE：锁住这行直到 commit
    )
    target = result.scalars().first()
    if not target:
        raise BusinessException(ErrorCode.USER_NOT_FOUND, f"用户不存在: {user_id}")

    # ---- 逐字段覆盖 ----
    # 用户名（改了才校验唯一性）
    if body.username != target.username:
        await _validate_username_unique(db, body.username)
        target.username = body.username

    # 密码（空 = 不修改）
    if body.password:
        target.password_hash = await hash_password(body.password)

    target.display_name = body.display_name
    target.phone = body.phone

    # 禁用保护：不能禁用最后一个管理员
    if not body.is_active:
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

    target.is_active = body.is_active

    # 部门
    await _resolve_user_dept(db, body.department_id)
    target.department_id = body.department_id

    # 角色
    old_role_ids = {r.id for r in target.roles}
    await _resolve_user_roles(db, target, body.role_ids)
    roles_changed = {r.id for r in target.roles} != old_role_ids

    # ---- 提交 ----
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")
    await db.refresh(target)

    # ---- 角色变更 → 清除权限缓存（下次请求重新从 DB 加载）----
    if roles_changed:
        try:
            await redis_client.delete(f"perm:{user_id}")
        except aioredis.RedisError:
            pass  # Redis 故障不影响用户更新

    return ApiResponse.ok(data=target, message="更新成功")


# ============================================================
# 7. PATCH /users/{user_id} — 部分更新
# ============================================================

@router.patch("/{user_id}", response_model=UserReadResponse, summary="部分更新用户")
async def patch_user(
    user_id: int,
    body: UserPatch,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.UPDATE])],
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """#7 PATCH 部分更新。

    model_dump(exclude_unset=True) 是关键：
      前端只传 { is_active: false } → data 里只有 is_active，其他字段不动

    前端使用场景：
      - 点击"禁用/启用"按钮 → PATCH { is_active: false/true }
      - 快速编辑某个字段 → PATCH { display_name: "新名字" }
    """
    # 行级锁 + 预加载
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles), selectinload(User.department))
        .where(User.id == user_id)
        .with_for_update()
    )
    target = result.scalars().first()
    if not target:
        raise BusinessException(ErrorCode.USER_NOT_FOUND, f"用户不存在: {user_id}")

    # exclude_unset=True：只包含前端传了的字段
    data = body.model_dump(exclude_unset=True)

    # ---- 逐个检查前端传了哪些字段 ----
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
        target.phone = data["phone"]  # null 表示清空手机号

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

    # 角色变更 → 清除权限缓存
    if "role_ids" in data:
        try:
            await redis_client.delete(f"perm:{user_id}")
        except aioredis.RedisError:
            pass

    return ApiResponse.ok(data=target, message="更新成功")


# ============================================================
# 8. DELETE /users/{user_id} — 软禁用 / 硬删除
# ============================================================

@router.delete("/{user_id}", response_model=ApiResponse, summary="禁用/删除用户")
async def delete_user(
    user_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[UserScope.DELETE])],
    hard: bool = Query(False, description="true=彻底删除（仅限已禁用的用户），默认 false=软禁用"),
    redis_client: aioredis.Redis = Depends(get_redis),
):
    """#8 两种删除模式。

    ?hard=false（默认软禁用）：
      - 设置 is_active = False
      - 用户数据保留，只是不能登录
      - 前端列表显示为"已禁用"状态

    ?hard=true（硬删除）：
      - 物理删除数据库记录
      - 前提：用户已经处于禁用状态（防止误删活跃用户）
      - 管理员保护：不能删除最后一个管理员
      - 不能删除自己
    """
    # 行级锁
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id).with_for_update()
    )
    target = result.scalars().first()
    if not target:
        raise BusinessException(ErrorCode.USER_NOT_FOUND, f"用户不存在: {user_id}")

    # 安全约束
    if user.id == user_id:
        raise BusinessException(ErrorCode.CONFLICT, "不允许操作自己的账号")
    if target.username == "admin":
        raise BusinessException(ErrorCode.USER_CANNOT_DISABLE_SUPERADMIN, "不允许操作超级管理员")

    if hard:
        # ---- 硬删除 ----
        if target.is_active:
            raise BusinessException(ErrorCode.CONFLICT, "不允许彻底删除启用状态的用户，请先禁用")

        # 管理员保护：即使用户已禁用，也不能删最后一个管理员
        if any(r.code == "admin" for r in target.roles):
            admin_count = (await db.execute(
                select(User).join(User.roles).where(
                    Role.code == "admin", User.is_active == True
                ).with_for_update()
            )).scalars().all()
            if len(admin_count) < 1:
                raise BusinessException(ErrorCode.CONFLICT, "不允许删除最后一个拥有管理员角色的用户")

        # 删前清除权限缓存
        try:
            await redis_client.delete(f"perm:{user_id}")
        except aioredis.RedisError:
            pass

        await db.delete(target)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            # 可能被其他表的外键引用（虽然已设 SET NULL/CASCADE，但仍有可能有未处理的关系）
            raise BusinessException(ErrorCode.CONFLICT, "删除失败：存在关联数据")
        return ApiResponse.ok(message="已彻底删除")
    else:
        # ---- 软禁用 ----
        if not target.is_active:
            raise BusinessException(ErrorCode.CONFLICT, "该用户已被禁用")

        # 管理员保护
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

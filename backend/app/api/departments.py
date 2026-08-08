"""
部门管理 API — 组织架构树形 CRUD。

与菜单管理几乎完全相同的模式：
  - parent_id 循环检测
  - 子部门变顶级（SET NULL）
  - 删除时统计受影响用户数
"""

from typing import Annotated

from fastapi import APIRouter, Security
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import DbSession
from app.core.dependencies import get_current_user
from app.core.exceptions import BusinessException, ErrorCode
from app.models import Department, User
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentPatch, DepartmentListResponse, DepartmentListApiResponse, DepartmentBriefResponse
from app.schemas.response import ApiResponse

router = APIRouter()


class DeptScope:
    LIST   = "department:list"
    CREATE = "department:create"
    UPDATE = "department:update"
    DELETE = "department:delete"


# ============================================================
# 1. 循环检测 — 与菜单相同的逻辑
# ============================================================

async def _would_create_cycle(db: AsyncSession, dept_id: int, new_parent_id: int) -> bool:
    """#1 检查 parent_id 变更是否会形成循环。沿父链向上遍历。"""
    current_id = new_parent_id
    visited: set[int] = set()
    while current_id is not None:
        if current_id == dept_id:
            return True
        if current_id in visited:
            break
        visited.add(current_id)
        result = await db.execute(
            select(Department.parent_id).where(Department.id == current_id)
        )
        row = result.first()
        current_id = row[0] if row else None
    return False


# ============================================================
# 2. GET /departments — 部门列表
# ============================================================

@router.get("", response_model=DepartmentListApiResponse, summary="部门列表")
async def list_departments(
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[DeptScope.LIST])],
):
    """#2 返回全部部门（扁平列表，前端用 parent_id 转树）。"""
    result = await db.execute(select(Department).order_by(Department.sort_order, Department.id))
    departments = result.scalars().all()
    data = DepartmentListResponse(
        items=[
            {
                "id": d.id, "code": d.code, "name": d.name,
                "parent_id": d.parent_id, "sort_order": d.sort_order,
                "description": d.description,
            }
            for d in departments
        ],
        total=len(departments),
    )
    return ApiResponse.ok(data=data)


# ============================================================
# 3. POST /departments — 创建部门
# ============================================================

@router.post("", response_model=DepartmentBriefResponse, status_code=201, summary="创建部门")
async def create_department(
    body: DepartmentCreate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[DeptScope.CREATE])],
):
    """#3 创建部门 — 验证父部门存在 + 双重唯一性保护。"""
    if (await db.execute(select(Department).where(Department.code == body.code))).scalars().first():
        raise BusinessException(ErrorCode.DEPT_CODE_EXISTS, "部门编码已存在")
    if body.parent_id is not None:
        parent = (await db.execute(select(Department).where(Department.id == body.parent_id))).scalars().first()
        if not parent:
            raise BusinessException(ErrorCode.DEPT_NOT_FOUND, f"父部门不存在: {body.parent_id}")
    dept = Department(
        code=body.code, name=body.name, parent_id=body.parent_id,
        sort_order=body.sort_order, description=body.description,
    )
    db.add(dept)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise BusinessException(ErrorCode.DEPT_CODE_EXISTS, "部门编码已存在")
    await db.refresh(dept)
    return ApiResponse.ok(data=dept, message="创建成功")


# ============================================================
# 4. PUT /departments/{dept_id} — 全量更新
# ============================================================

@router.put("/{dept_id}", response_model=DepartmentBriefResponse, summary="全量更新部门")
async def update_department(
    dept_id: int,
    body: DepartmentUpdate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[DeptScope.UPDATE])],
):
    """#4 PUT 全量更新 — 包含循环检测。"""
    result = await db.execute(
        select(Department).where(Department.id == dept_id).with_for_update()
    )
    dept = result.scalars().first()
    if not dept:
        raise BusinessException(ErrorCode.DEPT_NOT_FOUND, f"部门不存在: {dept_id}")

    # 校验父部门 + 循环检测
    if body.parent_id is not None:
        if body.parent_id == dept_id:
            raise BusinessException(ErrorCode.CONFLICT, "部门不能将自己设为父部门")
        parent = (await db.execute(select(Department).where(Department.id == body.parent_id))).scalars().first()
        if not parent:
            raise BusinessException(ErrorCode.DEPT_NOT_FOUND, f"父部门不存在: {body.parent_id}")
        if await _would_create_cycle(db, dept_id, body.parent_id):
            raise BusinessException(ErrorCode.CONFLICT, "不能将部门设置为自己的子孙部门")

    # 全量覆盖
    dept.name = body.name
    dept.parent_id = body.parent_id
    dept.sort_order = body.sort_order
    dept.description = body.description

    await db.commit()
    return ApiResponse.ok(data=dept, message="更新成功")


# ============================================================
# 5. PATCH /departments/{dept_id} — 部分更新
# ============================================================

@router.patch("/{dept_id}", response_model=DepartmentBriefResponse, summary="部分更新部门")
async def patch_department(
    dept_id: int,
    body: DepartmentPatch,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[DeptScope.UPDATE])],
):
    """#5 PATCH 部分更新 — 传什么改什么。"""
    result = await db.execute(
        select(Department).where(Department.id == dept_id).with_for_update()
    )
    dept = result.scalars().first()
    if not dept:
        raise BusinessException(ErrorCode.DEPT_NOT_FOUND, f"部门不存在: {dept_id}")

    data = body.model_dump(exclude_unset=True)

    if "name" in data:
        if data["name"] is None:
            raise BusinessException(ErrorCode.VALIDATION_ERROR, "name 不能为 null")
        dept.name = data["name"]
    if "description" in data:
        dept.description = data["description"]

    if "parent_id" in data:
        new_parent_id = data["parent_id"]
        if new_parent_id is not None:
            if new_parent_id == dept_id:
                raise BusinessException(ErrorCode.CONFLICT, "部门不能将自己设为父部门")
            parent = (await db.execute(select(Department).where(Department.id == new_parent_id))).scalars().first()
            if not parent:
                raise BusinessException(ErrorCode.DEPT_NOT_FOUND, f"父部门不存在: {new_parent_id}")
            if await _would_create_cycle(db, dept_id, new_parent_id):
                raise BusinessException(ErrorCode.CONFLICT, "不能将部门设置为自己的子孙部门")
        dept.parent_id = new_parent_id

    if "sort_order" in data:
        dept.sort_order = data["sort_order"]

    await db.commit()
    return ApiResponse.ok(data=dept, message="更新成功")


# ============================================================
# 6. DELETE /departments/{dept_id} — 删除部门
# ============================================================

@router.delete("/{dept_id}", response_model=ApiResponse, summary="删除部门")
async def delete_department(
    dept_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[DeptScope.DELETE])],
):
    """#6 删除部门 — 子部门变顶级 + 告知受影响用户数。

    删除部门的影响（FK 约束）：
      - 子部门 → parent_id 变 NULL（SET NULL）
      - 部门下用户 → department_id 变 NULL（SET NULL）
    用户和子部门都不会被删除，只是变成"无部门"状态。
    """
    result = await db.execute(
        select(Department).where(Department.id == dept_id).with_for_update()
    )
    dept = result.scalars().first()
    if not dept:
        raise BusinessException(ErrorCode.DEPT_NOT_FOUND, f"部门不存在: {dept_id}")

    # 子部门变顶级
    children = (await db.execute(
        select(Department).where(Department.parent_id == dept_id).with_for_update()
    )).scalars().all()
    child_info = None
    if children:
        child_names = [c.name for c in children]
        child_info = {"count": len(children), "children": child_names}
        for child in children:
            child.parent_id = None

    # 统计受影响用户（仅告知数量，不修改用户数据，FK 自动 SET NULL）
    user_count = (await db.execute(
        select(func.count()).select_from(User).where(User.department_id == dept_id)
    )).scalar() or 0

    await db.delete(dept)
    await db.commit()

    # 组装提示信息
    parts = []
    if child_info and child_info["count"] > 0:
        parts.append(f"{child_info['count']} 个子部门已变为顶级部门")
    if user_count > 0:
        parts.append(f"{user_count} 个用户部门已清空")
    message = "已删除" + ("，" + "、".join(parts) if parts else "")
    return ApiResponse.ok(
        message=message,
        data={"child_depts": child_info, "affected_users": user_count},
    )

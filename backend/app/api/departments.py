"""部门管理 API"""

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


async def _would_create_cycle(db: AsyncSession, dept_id: int, new_parent_id: int) -> bool:
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


@router.get("", response_model=DepartmentListApiResponse, summary="部门列表")
async def list_departments(
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[DeptScope.LIST])],
):
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


@router.post("", response_model=DepartmentBriefResponse, status_code=201, summary="创建部门")
async def create_department(
    body: DepartmentCreate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[DeptScope.CREATE])],
):
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


@router.put("/{dept_id}", response_model=DepartmentBriefResponse, summary="全量更新部门")
async def update_department(
    dept_id: int,
    body: DepartmentUpdate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[DeptScope.UPDATE])],
):
    """PUT 全量更新 —— 前端传所有字段（可空字段传 null），直接覆盖"""
    result = await db.execute(
        select(Department).where(Department.id == dept_id).with_for_update()
    )
    dept = result.scalars().first()
    if not dept:
        raise BusinessException(ErrorCode.DEPT_NOT_FOUND, f"部门不存在: {dept_id}")

    # 校验父部门
    if body.parent_id is not None:
        if body.parent_id == dept_id:
            raise BusinessException(ErrorCode.CONFLICT, "部门不能将自己设为父部门")
        parent = (await db.execute(select(Department).where(Department.id == body.parent_id))).scalars().first()
        if not parent:
            raise BusinessException(ErrorCode.DEPT_NOT_FOUND, f"父部门不存在: {body.parent_id}")
        if await _would_create_cycle(db, dept_id, body.parent_id):
            raise BusinessException(ErrorCode.CONFLICT, "不能将部门设置为自己的子孙部门")

    # 全量赋值
    dept.name = body.name
    dept.parent_id = body.parent_id
    dept.sort_order = body.sort_order
    dept.description = body.description

    await db.commit()
    return ApiResponse.ok(data=dept, message="更新成功")


@router.patch("/{dept_id}", response_model=DepartmentBriefResponse, summary="部分更新部门")
async def patch_department(
    dept_id: int,
    body: DepartmentPatch,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[DeptScope.UPDATE])],
):
    """PATCH 部分更新 —— 仅更新传了的字段（传 null 则清除该字段值）"""
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


@router.delete("/{dept_id}", response_model=ApiResponse, summary="删除部门")
async def delete_department(
    dept_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[DeptScope.DELETE])],
):
    result = await db.execute(
        select(Department).where(Department.id == dept_id).with_for_update()
    )
    dept = result.scalars().first()
    if not dept:
        raise BusinessException(ErrorCode.DEPT_NOT_FOUND, f"部门不存在: {dept_id}")
    # 子部门设为顶级
    children = (await db.execute(
        select(Department).where(Department.parent_id == dept_id).with_for_update()
    )).scalars().all()
    child_info = None
    if children:
        child_names = [c.name for c in children]
        child_info = {"count": len(children), "children": child_names}
        for child in children:
            child.parent_id = None
    # 统计受影响用户
    user_count = (await db.execute(
        select(func.count()).select_from(User).where(User.department_id == dept_id)
    )).scalar() or 0
    await db.delete(dept)
    await db.commit()
    parts = []
    if child_info and child_info["count"] > 0:
        parts.append(f"{child_info['count']} 个子部门已变为顶级部门")
    if user_count > 0:
        parts.append(f"{user_count} 个用户部门已清空")
    message = "已删除" + ("，" + "、".join(parts) if parts else "")
    return ApiResponse.ok(message=message, data={"child_depts": child_info, "affected_users": user_count})

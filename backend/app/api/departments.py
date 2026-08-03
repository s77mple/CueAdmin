"""部门管理 API"""

from typing import Annotated

from fastapi import APIRouter, Security
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import DbSession
from app.core.dependencies import get_current_user
from app.core.exceptions import BusinessException, ErrorCode
from app.models import Department, User
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentListResponse, DepartmentListApiResponse, DepartmentBriefResponse
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
        raise BusinessException(ErrorCode.CONFLICT, "部门编码已存在")
    if body.parent_id is not None:
        parent = (await db.execute(select(Department).where(Department.id == body.parent_id))).scalars().first()
        if not parent:
            raise BusinessException(ErrorCode.NOT_FOUND, f"父部门不存在: {body.parent_id}")
    dept = Department(
        code=body.code, name=body.name, parent_id=body.parent_id,
        sort_order=body.sort_order, description=body.description,
    )
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return ApiResponse.ok(data=dept, message="创建成功")


@router.put("/{dept_id}", response_model=DepartmentBriefResponse, summary="更新部门")
async def update_department(
    dept_id: int,
    body: DepartmentUpdate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[DeptScope.UPDATE])],
):
    result = await db.execute(
        select(Department).where(Department.id == dept_id).with_for_update()
    )
    dept = result.scalars().first()
    if not dept:
        raise BusinessException(ErrorCode.NOT_FOUND, f"部门不存在: {dept_id}")
    if body.name is not None:
        dept.name = body.name
    if body.description is not None:
        dept.description = body.description
    if "parent_id" in body.model_dump(exclude_unset=True):
        new_parent_id = body.parent_id
        if new_parent_id is not None:
            if new_parent_id == dept_id:
                raise BusinessException(ErrorCode.CONFLICT, "部门不能将自己设为父部门")
            parent = (await db.execute(select(Department).where(Department.id == new_parent_id))).scalars().first()
            if not parent:
                raise BusinessException(ErrorCode.NOT_FOUND, f"父部门不存在: {new_parent_id}")
            if await _would_create_cycle(db, dept_id, new_parent_id):
                raise BusinessException(ErrorCode.CONFLICT, "不能将部门设置为自己的子孙部门")
        dept.parent_id = new_parent_id
    if body.sort_order is not None:
        dept.sort_order = body.sort_order
    await db.commit()
    return ApiResponse.ok(data=dept, message="更新成功")


@router.delete("/{dept_id}", response_model=ApiResponse, summary="删除部门")
async def delete_department(
    dept_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[DeptScope.DELETE])],
):
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalars().first()
    if not dept:
        raise BusinessException(ErrorCode.NOT_FOUND, f"部门不存在: {dept_id}")
    # 子部门设为顶级
    children = (await db.execute(
        select(Department).where(Department.parent_id == dept_id)
    )).scalars().all()
    child_info = None
    if children:
        child_names = [c.name for c in children]
        child_info = {"count": len(children), "children": child_names}
        for child in children:
            child.parent_id = None
    await db.delete(dept)
    await db.commit()
    if child_info:
        return ApiResponse.ok(
            message=f"已删除，{child_info['count']} 个子部门已变为顶级部门",
            data=child_info,
        )
    return ApiResponse.ok(message="删除成功")

"""
部门管理 API — 薄控制器，业务逻辑全部委托给 DepartmentService。
"""

from typing import Annotated

from fastapi import APIRouter, Path, Security

from app.core.database import SessionDep
from app.core.dependencies import get_current_user
from app.models import User
from app.schemas.department import (
    DepartmentCreate, DepartmentUpdate,
    DepartmentListResponse, DepartmentBrief,
)
from app.schemas.response import ApiResponse
from app.services.department_service import DepartmentService

router = APIRouter()


class DeptScope:
    LIST   = "department:list"
    CREATE = "department:create"
    UPDATE = "department:update"
    DELETE = "department:delete"


# ============================================================
# GET /departments — 部门列表
# ============================================================

@router.get("", response_model=ApiResponse[DepartmentListResponse], summary="部门列表")
async def list_departments(
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[DeptScope.LIST])],
) -> ApiResponse[DepartmentListResponse]:
    departments = await DepartmentService(session).list_departments()
    data = DepartmentListResponse(items=departments, total=len(departments))
    return ApiResponse.ok(data=data)


# ============================================================
# POST /departments — 创建部门
# ============================================================

@router.post("", response_model=ApiResponse[DepartmentBrief], status_code=201, summary="创建部门")
async def create_department(
    body: DepartmentCreate,
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[DeptScope.CREATE])],
) -> ApiResponse[DepartmentBrief]:
    dept = await DepartmentService(session).create_department(body)
    return ApiResponse.ok(data=dept, message="创建成功")


# ============================================================
# PUT /departments/{dept_id} — 全量更新
# ============================================================

@router.put("/{dept_id}", response_model=ApiResponse[DepartmentBrief], summary="全量更新部门")
async def update_department(
    dept_id: Annotated[int, Path(description="部门 ID")],
    body: DepartmentUpdate,
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[DeptScope.UPDATE])],
) -> ApiResponse[DepartmentBrief]:
    dept = await DepartmentService(session).update_department(dept_id, body)
    return ApiResponse.ok(data=dept, message="更新成功")


# ============================================================
# DELETE /departments/{dept_id} — 删除部门
# ============================================================

@router.delete("/{dept_id}", response_model=ApiResponse, summary="删除部门")
async def delete_department(
    dept_id: Annotated[int, Path(description="部门 ID")],
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[DeptScope.DELETE])],
) -> ApiResponse:
    result = await DepartmentService(session).delete_department(dept_id)
    return ApiResponse.ok(message=result["message"])

"""部门 Schema — 创建/更新/查询的数据结构。

部门管理的特点：
  - 树形结构（与菜单相同的自引用模式）
  - 删除部门 → 子部门变顶级（SET NULL）
  - 删除部门 → 用户的 department_id 变 NULL（SET NULL）
  - 不允许产生循环引用
"""

from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=50)
    parent_id: int | None = None             # null = 顶级部门
    sort_order: int = Field(0, ge=0)
    description: str | None = Field(None, max_length=500)


class DepartmentUpdate(BaseModel):
    """PUT 全量更新 — code 不可修改，其余所有字段必传。"""
    name: str = Field(..., min_length=1, max_length=50, description="部门名称")
    parent_id: int | None = Field(..., description="父部门 ID，顶级部门传 null")
    sort_order: int = Field(..., ge=0, description="排序号")
    description: str | None = Field(..., max_length=500, description="描述，无则传 null")


class DepartmentPatch(BaseModel):
    """PATCH 部分更新 — 只传要改的字段。"""
    name: str | None = Field(None, min_length=1, max_length=50)
    parent_id: int | None = None
    sort_order: int | None = Field(None, ge=0)
    description: str | None = Field(None, max_length=500)


# ============================================================
# 响应 Schema
# ============================================================

class DepartmentItem(BaseModel):
    """部门列表项 — 扁平列表，前端转树。"""
    id: int
    code: str
    name: str
    parent_id: int | None = None
    sort_order: int
    description: str | None = None

    model_config = {"from_attributes": True}


class DepartmentListResponse(BaseModel):
    items: list[DepartmentItem]
    total: int


class DepartmentBrief(BaseModel):
    """部门简要信息 — 嵌套在用户响应中。"""
    id: int
    code: str
    name: str
    parent_id: int | None = None

    model_config = {"from_attributes": True}


# —————— 响应包装 ——————
from app.schemas.response import ApiResponse


class DepartmentListApiResponse(ApiResponse[DepartmentListResponse]):
    pass


class DepartmentBriefResponse(ApiResponse[DepartmentBrief]):
    pass

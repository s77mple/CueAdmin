"""部门 Schema"""

from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=50)
    parent_id: int | None = None
    sort_order: int = Field(0, ge=0)
    description: str | None = Field(None, max_length=500)


class DepartmentUpdate(BaseModel):
    """全量更新（PUT）—— 所有字段必传，可空字段传 null（code 不可修改）"""
    name: str = Field(..., min_length=1, max_length=50, description="部门名称")
    parent_id: int | None = Field(..., description="父部门 ID，顶级部门传 null")
    sort_order: int = Field(..., ge=0, description="排序号")
    description: str | None = Field(..., max_length=500, description="描述，无则传 null")


class DepartmentPatch(BaseModel):
    """部分更新（PATCH）—— 仅传需要修改的字段"""
    name: str | None = Field(None, min_length=1, max_length=50)
    parent_id: int | None = None
    sort_order: int | None = Field(None, ge=0)
    description: str | None = Field(None, max_length=500)


class DepartmentItem(BaseModel):
    id: int
    code: str
    name: str
    parent_id: int | None = None
    sort_order: int
    description: str | None = None


class DepartmentListResponse(BaseModel):
    items: list[DepartmentItem]
    total: int


class DepartmentBrief(BaseModel):
    id: int
    code: str
    name: str
    parent_id: int | None = None

    model_config = {"from_attributes": True}


# —————— 响应类型 ——————
from app.schemas.response import ApiResponse


class DepartmentListApiResponse(ApiResponse[DepartmentListResponse]):
    pass


class DepartmentBriefResponse(ApiResponse[DepartmentBrief]):
    pass

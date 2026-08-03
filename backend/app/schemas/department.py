"""部门 Schema"""

from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=50)
    parent_id: int | None = None
    sort_order: int = 0
    description: str | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    sort_order: int | None = None
    description: str | None = None


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

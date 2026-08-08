"""权限 Schema"""

from pydantic import BaseModel, Field


class PermissionCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    resource: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=1, max_length=50)
    description: str | None = Field(None, max_length=200)


class PermissionUpdate(BaseModel):
    """全量更新（PUT）—— 所有字段必传，可空字段传 null（code 允许修改）"""
    code: str = Field(..., min_length=1, max_length=100, description="权限码")
    name: str = Field(..., min_length=1, max_length=100, description="权限名称")
    resource: str = Field(..., min_length=1, max_length=50, description="资源标识")
    action: str = Field(..., min_length=1, max_length=50, description="操作标识")
    description: str | None = Field(..., max_length=200, description="描述，无则传 null")


class PermissionPatch(BaseModel):
    """部分更新（PATCH）—— 仅传需要修改的字段"""
    code: str | None = Field(None, min_length=1, max_length=100)
    name: str | None = Field(None, min_length=1, max_length=100)
    resource: str | None = Field(None, min_length=1, max_length=50)
    action: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = Field(None, max_length=200)

class PermissionItem(BaseModel):
    id: int
    code: str
    name: str
    resource: str
    action: str
    description: str | None = None

class PermissionListResponse(BaseModel):
    items: list[PermissionItem]
    total: int


class PermissionBrief(BaseModel):
    id: int
    code: str
    name: str
    resource: str

    model_config = {"from_attributes": True}


# —————— 响应类型 ——————
from app.schemas.response import ApiResponse


class PermissionListApiResponse(ApiResponse[PermissionListResponse]):
    pass


class PermissionBriefResponse(ApiResponse[PermissionBrief]):
    pass
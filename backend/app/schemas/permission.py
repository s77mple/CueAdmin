"""权限 Schema"""

from pydantic import BaseModel, Field


class PermissionCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    resource: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=1, max_length=50)
    description: str | None = Field(None, max_length=200)


class PermissionUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    resource: str | None = None
    action: str | None = None
    description: str | None = None

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

    model_config = {"from_attributes": True}


# —————— 响应类型 ——————
from app.schemas.response import ApiResponse


class PermissionListApiResponse(ApiResponse[PermissionListResponse]):
    pass


class PermissionBriefResponse(ApiResponse[PermissionBrief]):
    pass
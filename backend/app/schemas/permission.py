"""权限 Schema"""

from pydantic import BaseModel


class PermissionCreate(BaseModel):
    code: str
    name: str
    resource: str
    action: str
    description: str | None = None


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
"""角色 Schema"""

from pydantic import BaseModel, Field


class RoleCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=50)
    description: str | None = Field(None, max_length=200)
    permission_codes: list[str] = []   # 权限 code 列表（如 "user:list"），非 ID
    menu_ids: list[int] = []           # 菜单 ID 列表


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    permission_codes: list[str] | None = None
    menu_ids: list[int] | None = None


from app.schemas.permission import PermissionBrief
from app.schemas.menu import MenuBrief


class RoleItem(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
    is_system: bool
    permissions: list[PermissionBrief] = []
    menus: list[MenuBrief] = []


class RoleListResponse(BaseModel):
    items: list[RoleItem]
    total: int


class RoleBrief(BaseModel):
    id: int
    code: str
    name: str

    model_config = {"from_attributes": True}


# —————— 响应类型 ——————
from app.schemas.response import ApiResponse


class RoleListApiResponse(ApiResponse[RoleListResponse]):
    pass


class RoleBriefResponse(ApiResponse[RoleBrief]):
    pass

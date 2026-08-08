"""角色 Schema"""

from pydantic import BaseModel, Field


class RoleCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=50)
    description: str | None = Field(None, max_length=200)
    permission_codes: list[str] = Field(default=[], max_length=200)   # 权限 code 列表（如 "user:list"），非 ID
    menu_ids: list[int] = Field(default=[], max_length=200)           # 菜单 ID 列表


class RoleUpdate(BaseModel):
    """全量更新（PUT）—— 所有字段必传，可空字段传 null（code 不可修改）"""
    name: str = Field(..., min_length=2, max_length=50, description="角色名称")
    description: str | None = Field(..., max_length=200, description="描述，无则传 null")
    permission_codes: list[str] = Field(..., max_length=200, description="权限 code 列表，可为空数组")
    menu_ids: list[int] = Field(..., max_length=200, description="菜单 ID 列表，可为空数组")


class RolePatch(BaseModel):
    """部分更新（PATCH）—— 仅传需要修改的字段"""
    name: str | None = Field(None, min_length=2, max_length=50)
    description: str | None = Field(None, max_length=200)
    permission_codes: list[str] | None = Field(None, max_length=200)
    menu_ids: list[int] | None = Field(None, max_length=200)


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

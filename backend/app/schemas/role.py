"""角色 Schema — 创建/更新/查询的数据结构。

角色管理的特殊性：
  - permission_codes 用 code 而不是 id（因为权限 code 有语义，id 无意义）
  - menu_ids 用 id（菜单 id 更稳定，code 可能重复）
  - is_system 角色不允许删除和修改 code
"""

from pydantic import BaseModel, Field


class RoleCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=50)
    description: str | None = Field(None, max_length=200)
    permission_codes: list[str] = Field(default=[], max_length=200)   # 权限用 code（语义化）
    menu_ids: list[int] = Field(default=[], max_length=200)           # 菜单用 id（更稳定）


class RoleUpdate(BaseModel):
    """PUT 全量更新 — code 不可修改，其余所有字段必传。"""
    name: str = Field(..., min_length=2, max_length=50, description="角色名称")
    description: str | None = Field(..., max_length=200, description="描述，无则传 null")
    permission_codes: list[str] = Field(..., max_length=200, description="权限 code 列表，可为空数组")
    menu_ids: list[int] = Field(..., max_length=200, description="菜单 ID 列表，可为空数组")


class RolePatch(BaseModel):
    """PATCH 部分更新 — 只传要改的字段。"""
    name: str | None = Field(None, min_length=2, max_length=50)
    description: str | None = Field(None, max_length=200)
    permission_codes: list[str] | None = Field(None, max_length=200)
    menu_ids: list[int] | None = Field(None, max_length=200)


# ============================================================
# 响应 Schema
# ============================================================

from app.schemas.permission import PermissionBrief
from app.schemas.menu import MenuBrief


class RoleItem(BaseModel):
    """角色列表项 — 带权限和菜单的子列表。"""
    id: int
    code: str
    name: str
    description: str | None = None
    is_system: bool
    permissions: list[PermissionBrief] = []
    menus: list[MenuBrief] = []

    model_config = {"from_attributes": True}


class RoleBrief(BaseModel):
    """角色简要信息 — 嵌套在用户响应中。"""
    id: int
    code: str
    name: str

    model_config = {"from_attributes": True}


# —————— 响应包装 ——————
from app.schemas.response import ApiResponse, PageData


class RoleListApiResponse(ApiResponse[PageData[RoleItem]]):
    pass


class RoleBriefResponse(ApiResponse[RoleBrief]):
    pass

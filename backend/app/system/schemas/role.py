"""角色 Schema — 创建/更新/查询的数据结构。

角色管理的特殊性：
  - permission_codes 用 code 而不是 id（因为权限 code 有语义，id 无意义）
  - menu_ids 用 id（菜单 id 更稳定，code 可能重复）
  - is_system 角色不允许删除和修改 code
"""

from typing import Annotated

from pydantic import BaseModel, Field


class RoleCreate(BaseModel):
    code: Annotated[str, Field(
        min_length=2, max_length=50,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="角色编码，创建后不可修改，小写字母开头，仅含小写字母/数字/下划线",
    )]
    name: Annotated[str, Field(min_length=2, max_length=50, description="角色名称")]
    description: Annotated[str | None, Field(max_length=200, description="描述，无则不传")] = None
    permission_codes: Annotated[list[str], Field(default_factory=list, max_length=200, description="权限 code 列表，可为空数组")]  # 权限用 code（语义化）
    menu_ids: Annotated[list[int], Field(default_factory=list, max_length=200, description="菜单 ID 列表，可为空数组")]  # 菜单用 id（更稳定）


class RoleUpdate(BaseModel):
    """PUT 全量更新 — code 不可修改，其余所有字段必传。"""
    name: Annotated[str, Field(min_length=2, max_length=50, description="角色名称")]
    description: Annotated[str | None, Field(max_length=200, description="描述，无则传 null")]
    permission_codes: Annotated[list[str], Field(max_length=200, description="权限 code 列表，可为空数组")]
    menu_ids: Annotated[list[int], Field(max_length=200, description="菜单 ID 列表，可为空数组")]


# 响应 Schema

from app.system.schemas.permission import PermissionBrief
from app.system.schemas.menu import MenuBrief


class RoleItem(BaseModel):
    """角色列表项 — 带权限和菜单的子列表。"""
    id: int
    code: str
    name: str
    description: str | None = None
    is_system: bool
    permissions: Annotated[list[PermissionBrief], Field(default_factory=list)]
    menus: Annotated[list[MenuBrief], Field(default_factory=list)]

    model_config = {"from_attributes": True}


class RoleBrief(BaseModel):
    """角色简要信息 — 嵌套在用户响应中。"""
    id: int
    code: str
    name: str

    model_config = {"from_attributes": True}

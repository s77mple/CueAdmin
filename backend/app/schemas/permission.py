"""权限 Schema — 创建/更新/查询的数据结构。

权限码格式：{resource}:{action}
  resource: user, role, menu, permission, department
  action:   list, create, update, delete
  → 5 资源 × 4 操作 = 20 个权限码

前端用法：
  v-perms="['user:create']" → 检查当前用户是否有此权限
"""

from typing import Annotated

from pydantic import BaseModel, Field


class PermissionCreate(BaseModel):
    code: Annotated[str, Field(min_length=1, max_length=100, description="权限码，格式 {resource}:{action}")]
    name: Annotated[str, Field(min_length=1, max_length=100, description="权限名称")]
    resource: Annotated[str, Field(min_length=1, max_length=50, description="资源标识，如 user/role/menu")]
    action: Annotated[str, Field(min_length=1, max_length=50, description="操作标识，如 list/create/update/delete")]
    description: Annotated[str | None, Field(max_length=200, description="描述，无则不传")] = None


class PermissionUpdate(BaseModel):
    """PUT 全量更新 — code 允许修改，所有字段必传。"""
    code: Annotated[str, Field(min_length=1, max_length=100, description="权限码")]
    name: Annotated[str, Field(min_length=1, max_length=100, description="权限名称")]
    resource: Annotated[str, Field(min_length=1, max_length=50, description="资源标识")]
    action: Annotated[str, Field(min_length=1, max_length=50, description="操作标识")]
    description: Annotated[str | None, Field(max_length=200, description="描述，无则传 null")]


# ============================================================
# 响应 Schema
# ============================================================

class PermissionItem(BaseModel):
    """权限列表项。"""
    id: int
    code: str
    name: str
    resource: str
    action: str
    description: str | None = None

    model_config = {"from_attributes": True}


class PermissionBrief(BaseModel):
    """权限简要信息 — 嵌套在角色响应中。"""
    id: int
    code: str
    name: str
    resource: str

    model_config = {"from_attributes": True}


class PermissionListResponse(BaseModel):
    """权限列表响应 — 扁平列表，前端按 resource 分组转树。"""
    items: list[PermissionItem]
    total: int

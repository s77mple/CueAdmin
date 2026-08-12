"""权限 Schema — 创建/更新/查询的数据结构。

权限码格式：{resource}:{action}
  resource: user, role, menu, permission, department
  action:   list, create, update, delete
  → 5 资源 × 4 操作 = 20 个权限码

前端用法：
  v-perms="['user:create']" → 检查当前用户是否有此权限
"""

from pydantic import BaseModel, Field


class PermissionCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    resource: str = Field(..., min_length=1, max_length=50)
    action: str = Field(..., min_length=1, max_length=50)
    description: str | None = Field(None, max_length=200)


class PermissionUpdate(BaseModel):
    """PUT 全量更新 — code 允许修改，所有字段必传。"""
    code: str = Field(..., min_length=1, max_length=100, description="权限码")
    name: str = Field(..., min_length=1, max_length=100, description="权限名称")
    resource: str = Field(..., min_length=1, max_length=50, description="资源标识")
    action: str = Field(..., min_length=1, max_length=50, description="操作标识")
    description: str | None = Field(..., max_length=200, description="描述，无则传 null")


class PermissionPatch(BaseModel):
    """PATCH 部分更新 — 只传要改的字段。"""
    code: str | None = Field(None, min_length=1, max_length=100)
    name: str | None = Field(None, min_length=1, max_length=100)
    resource: str | None = Field(None, min_length=1, max_length=50)
    action: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = Field(None, max_length=200)


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


class PermissionListResponse(BaseModel):
    items: list[PermissionItem]
    total: int


class PermissionBrief(BaseModel):
    """权限简要信息 — 嵌套在角色响应中。"""
    id: int
    code: str
    name: str
    resource: str

    model_config = {"from_attributes": True}


# —————— 响应包装 ——————
from app.schemas.response import ApiResponse


class PermissionListApiResponse(ApiResponse[PermissionListResponse]):
    pass


class PermissionBriefResponse(ApiResponse[PermissionBrief]):
    pass

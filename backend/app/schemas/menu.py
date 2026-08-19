"""菜单 Schema — 创建/更新/查询的数据结构。

菜单的两种类型：
  目录菜单：component=null, path=/system    → 纯文件夹，不可点击
  页面菜单：component=system/users/index   → 对应 src/views/ 下的 Vue 文件

前端动态路由匹配：
  addAsyncRoutes() 中 component 字符串匹配 import.meta.glob 的 key
  例 component="system/users/index" → /src/views/system/users/index.vue
"""

from typing import Annotated

from pydantic import BaseModel, Field


class MenuCreate(BaseModel):
    code: Annotated[str, Field(min_length=1, max_length=50, description="菜单编码，创建后不可修改")]
    name: Annotated[str, Field(min_length=1, max_length=50, description="菜单名称")]
    icon: Annotated[str | None, Field(max_length=50, description="图标，如 fa-solid:users")] = None
    path: Annotated[str | None, Field(max_length=100, description="路由路径，如 /users")] = None
    component: Annotated[str | None, Field(max_length=200, description="组件路径，如 system/users/index")] = None
    parent_id: Annotated[int | None, Field(description="父菜单 ID，顶级菜单传 null")] = None  # null = 顶级菜单
    sort_order: Annotated[int, Field(ge=0, description="排序号，越小越靠前")] = 0  # ge=0：不允许负数


class MenuUpdate(BaseModel):
    """PUT 全量更新 — code 不可修改，其余所有字段必传。"""
    name: Annotated[str, Field(min_length=1, max_length=50, description="菜单名称")]
    icon: Annotated[str | None, Field(max_length=50, description="图标，无则传 null")]
    path: Annotated[str | None, Field(max_length=100, description="路由路径，无则传 null")]
    component: Annotated[str | None, Field(max_length=200, description="组件路径，无则传 null")]
    parent_id: Annotated[int | None, Field(description="父菜单 ID，顶级菜单传 null")]
    sort_order: Annotated[int, Field(ge=0, description="排序号")]


# ============================================================
# 响应 Schema
# ============================================================

class MenuItem(BaseModel):
    """菜单列表项 — 扁平列表，前端转树。"""
    id: int
    code: str
    name: str
    icon: str | None = None
    path: str | None = None
    component: str | None = None
    parent_id: int | None = None
    sort_order: int

    model_config = {"from_attributes": True}


class MenuListResponse(BaseModel):
    items: list[MenuItem]
    total: int


class MenuBrief(BaseModel):
    """菜单简要信息 — 嵌套在角色响应中。"""
    id: int
    code: str
    name: str
    parent_id: int | None = None

    model_config = {"from_attributes": True}

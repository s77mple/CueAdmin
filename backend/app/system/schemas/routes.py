"""动态路由 Schema — 与 api/routes.py 对应。

RoutesResponse 是 GET /api/v1/routes 返回的数据结构（前端 initRouter() 的数据源）：
  routes      → 动态路由树
  permissions → 权限码列表（回写 pinia）
  roles       → 角色列表（回写 pinia）
"""

from typing import Annotated

from pydantic import BaseModel, Field

from app.system.schemas.role import RoleBrief


class RoutesResponse(BaseModel):
    """动态路由响应 — /routes 返回的数据。

    routes      → 前端 initRouter() 生成动态路由 + 侧边栏
    permissions → 回写 pinia，刷新按钮权限（改了权限不用重新登录）
    roles       → 回写 pinia，刷新角色（admin 判断 + 侧边栏过滤）
    """
    routes: Annotated[list[dict], Field(description="动态路由树")]
    permissions: Annotated[list[str], Field(description="权限码列表")]
    roles: Annotated[list[RoleBrief], Field(description="角色列表")]

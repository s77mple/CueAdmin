"""当前用户 Schema — 与 api/me.py 对应。

me 领域是"当前用户自己的数据"（只需登录、无需鉴权），与 auth 的登录登出分开：

  - RoutesResponse → GET /api/v1/routes 返回的动态路由 + 权限 + 角色
    （前端 initRouter() 的数据源，登录/刷新都会调）

将来 /me（个人信息）、/profile 等"当前用户"端点也放这里。
"""

from typing import Annotated

from pydantic import BaseModel, Field

from app.schemas.role import RoleBrief


class RoutesResponse(BaseModel):
    """动态路由响应 — /routes 返回的数据。

    routes      → 前端 initRouter() 生成动态路由 + 侧边栏
    permissions → 回写 pinia，刷新按钮权限（改了权限不用重新登录）
    roles       → 回写 pinia，刷新角色（admin 判断 + 侧边栏过滤）
    """
    routes: Annotated[list[dict], Field(default_factory=list)]
    permissions: Annotated[list[str], Field(default_factory=list)]
    roles: Annotated[list[RoleBrief], Field(default_factory=list)]

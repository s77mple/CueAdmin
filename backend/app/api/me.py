"""当前用户 API — 只需认证、无需鉴权的"当前用户自己"端点。

与 menus.py 的"菜单 CRUD 管理"区分：
  menus.py → 管理员维护菜单（需要 menu:list / menu:create 等权限）
  me.py    → 当前用户自己的数据（只需登录，不需要任何权限）

目前包含：
  GET /routes → 当前用户的动态路由 + 权限 + 角色（前端 initRouter() 的数据源）

将来 /me（个人信息）、/profile 等"当前用户"端点也放这里。
"""

from typing import Annotated

from fastapi import APIRouter, Security

from app.core.database import SessionDep
from app.core.dependencies import get_current_user
from app.models import User
from app.schemas.me import RoutesResponse
from app.schemas.response import ApiResponse
from app.services.menu_service import collect_user_menus, build_routes

routes_router = APIRouter()  # 挂载在 /routes（前端导航数据源）


@routes_router.get("", response_model=ApiResponse[RoutesResponse], summary="获取当前用户动态路由")
async def get_routes(
    session: SessionDep,
    user: Annotated[User, Security(get_current_user)],  # 仅认证不鉴权（不需要 scope）
) -> ApiResponse[RoutesResponse]:
    """返回当前用户的路由树 + 权限 + 角色，前端刷新时一并回写。

    routes       → 前端 initRouter() 生成动态路由 + 侧边栏
    permissions  → 前端回写 pinia，刷新按钮权限（改了权限不用重新登录）
    roles        → 前端回写 pinia，刷新角色（admin 判断 + 侧边栏过滤）

    前端调用时机：
      - 登录成功后 → getAsyncRoutes()
      - 刷新页面后 → router.beforeEach 检测到无路由数据 → initRouter() → getAsyncRoutes()

    菜单收集和路由构建统一收口到 menu_service，与 login 共用。
    遇到循环引用时跳过问题节点（graceful degradation），不崩溃。

    权限和角色能在这里直接取，是因为 get_current_user 对无 scopes 的请求
    也会 selectinload(Role.permissions)（见 dependencies.py #3.5）。
    """
    menus = await collect_user_menus(session, user)
    routes = build_routes(menus)
    permissions = sorted({p.code for role in user.roles for p in role.permissions})
    roles = [{"id": r.id, "code": r.code, "name": r.name} for r in user.roles]
    return ApiResponse.ok(
        data=RoutesResponse(routes=routes, permissions=permissions, roles=roles)
    )

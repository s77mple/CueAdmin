"""动态路由 API — 当前用户的动态路由 + 权限 + 角色（前端 initRouter 的数据源）。"""

from typing import Annotated

from fastapi import APIRouter, Security

from app.core.dependencies import SessionDep, get_current_user
from app.core.response import ApiResponse
from app.models import User
from app.schemas.routes import RoutesResponse
from app.services.menu_service import build_routes, collect_user_menus

router = APIRouter(prefix="/routes", tags=["动态路由"])


@router.get("", response_model=ApiResponse[RoutesResponse], summary="获取当前用户动态路由")
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
    也会 selectinload(Role.permissions)。
    """
    menus = await collect_user_menus(session, user)
    routes = build_routes(menus)
    permissions = sorted({p.code for role in user.roles for p in role.permissions})
    return ApiResponse.ok(
        data=RoutesResponse(
            routes=routes,
            permissions=permissions,
            roles=user.roles,  # ORM Role 列表 → 自动转 list[RoleBrief]（from_attributes）
        )
    )

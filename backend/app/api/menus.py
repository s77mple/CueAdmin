"""
菜单管理 API — 薄控制器，业务逻辑全部委托给 MenuService。

同时包含动态路由端点（GET /routes），返回 Pure Admin 格式的导航菜单数据，
是前端 initRouter() 的数据源。见文件末尾的 get_routes()。
"""

from typing import Annotated

from fastapi import APIRouter, Path, Security

from app.core.database import DbSession
from app.core.dependencies import get_current_user
from app.models import User
from app.schemas.menu import (
    MenuCreate, MenuUpdate,
    MenuListResponse, MenuListApiResponse, MenuBriefResponse,
)
from app.schemas.response import ApiResponse
from app.services.menu_service import (
    MenuService, collect_user_menus, build_routes,
)

router = APIRouter()
routes_router = APIRouter()  # 动态路由，单独挂载 /routes（前端导航数据源）


class MenuScope:
    LIST   = "menu:list"
    CREATE = "menu:create"
    UPDATE = "menu:update"
    DELETE = "menu:delete"


# ============================================================
# GET /menus — 菜单列表
# ============================================================

@router.get("", response_model=MenuListApiResponse, summary="菜单列表")
async def list_menus(
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.LIST])],
):
    menus = await MenuService(db).list_menus()
    data = MenuListResponse(items=menus, total=len(menus))
    return ApiResponse.ok(data=data)


# ============================================================
# POST /menus — 创建菜单
# ============================================================

@router.post("", response_model=MenuBriefResponse, status_code=201, summary="创建菜单")
async def create_menu(
    body: MenuCreate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.CREATE])],
):
    menu = await MenuService(db).create_menu(body)
    return ApiResponse.ok(data=menu, message="创建成功")


# ============================================================
# PUT /menus/{menu_id} — 全量更新
# ============================================================

@router.put("/{menu_id}", response_model=MenuBriefResponse, summary="全量更新菜单")
async def update_menu(
    menu_id: Annotated[int, Path(description="菜单 ID")],
    body: MenuUpdate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.UPDATE])],
):
    menu = await MenuService(db).update_menu(menu_id, body)
    return ApiResponse.ok(data=menu, message="更新成功")

# ============================================================
# DELETE /menus/{menu_id} — 删除菜单
# ============================================================

@router.delete("/{menu_id}", response_model=ApiResponse, summary="删除菜单")
async def delete_menu(
    menu_id: Annotated[int, Path(description="菜单 ID")],
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.DELETE])],
):
    result = await MenuService(db).delete_menu(menu_id)
    return ApiResponse.ok(message=result["message"])


# ============================================================
# GET /routes — 获取当前用户的动态路由
# ============================================================

@routes_router.get("", response_model=ApiResponse[list], summary="获取当前用户动态路由")
async def get_routes(
    db: DbSession,
    user: Annotated[User, Security(get_current_user)],  # 仅认证不鉴权（不需要 scope）
):
    """返回当前用户有权限看到的菜单，格式适配 Pure Admin。

    前端调用时机：
      - 登录成功后 → getAsyncRoutes()
      - 刷新页面后 → router.beforeEach 检测到无路由数据 → getMe() → getAsyncRoutes()

    菜单收集和路由构建统一收口到 menu_service，与 login、/me 共用。
    遇到循环引用时跳过问题节点（graceful degradation），不崩溃。
    """
    menus = await collect_user_menus(db, user)
    routes = build_routes(menus)
    return ApiResponse.ok(data=routes)

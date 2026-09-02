"""
菜单管理 API — 薄控制器，业务逻辑全部委托给 MenuService。

注意：动态路由端点（GET /routes）在 routes.py（当前用户模块），
因为 /routes 返回的是当前用户的路由 + 权限 + 角色，属于"当前用户"而非"菜单管理"。
"""

from typing import Annotated

from fastapi import APIRouter, Path, Security

from app.core.dependencies import SessionDep, get_current_user
from app.system.models import User
from app.system.schemas.menu import (
    MenuCreate, MenuUpdate,
    MenuItem, MenuListResponse, MenuBrief,
)
from app.core.response import ApiResponse
from app.system.services.menu_service import MenuService

router = APIRouter(prefix="/menus", tags=["菜单管理"])


class MenuScope:
    LIST   = "menu:list"
    CREATE = "menu:create"
    UPDATE = "menu:update"
    DELETE = "menu:delete"


# GET /menus — 菜单列表

@router.get("", response_model=ApiResponse[MenuListResponse], summary="菜单列表")
async def list_menus(
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.LIST])],
) -> ApiResponse[MenuListResponse]:
    menus = await MenuService(session).list_menus()
    data = MenuListResponse(items=menus, total=len(menus))
    return ApiResponse.ok(data=data)


# GET /menus/{menu_id} — 菜单详情（编辑回显）

@router.get("/{menu_id}", response_model=ApiResponse[MenuItem], summary="菜单详情")
async def get_menu(
    menu_id: Annotated[int, Path(description="菜单 ID")],
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.LIST])],
) -> ApiResponse[MenuItem]:
    menu = await MenuService(session).get_menu(menu_id)
    return ApiResponse.ok(data=menu)


# POST /menus — 创建菜单

@router.post("", response_model=ApiResponse[MenuBrief], status_code=201, summary="创建菜单")
async def create_menu(
    body: MenuCreate,
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.CREATE])],
) -> ApiResponse[MenuBrief]:
    menu = await MenuService(session).create_menu(body)
    return ApiResponse.ok(data=menu, message="创建成功")


# PUT /menus/{menu_id} — 全量更新

@router.put("/{menu_id}", response_model=ApiResponse[MenuBrief], summary="全量更新菜单")
async def update_menu(
    menu_id: Annotated[int, Path(description="菜单 ID")],
    body: MenuUpdate,
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.UPDATE])],
) -> ApiResponse[MenuBrief]:
    menu = await MenuService(session).update_menu(menu_id, body)
    return ApiResponse.ok(data=menu, message="更新成功")

# DELETE /menus/{menu_id} — 删除菜单

@router.delete("/{menu_id}", response_model=ApiResponse, summary="删除菜单")
async def delete_menu(
    menu_id: Annotated[int, Path(description="菜单 ID")],
    session: SessionDep,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.DELETE])],
) -> ApiResponse:
    result = await MenuService(session).delete_menu(menu_id)
    return ApiResponse.ok(message=result["message"])

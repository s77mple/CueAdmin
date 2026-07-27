"""菜单管理 API"""

from typing import Annotated

from fastapi import APIRouter, Security
from sqlalchemy import select

from app.core.database import DbSession
from app.core.dependencies import get_current_user
from app.core.exceptions import BusinessException, ErrorCode
from app.models import Menu, User
from app.schemas.menu import MenuCreate, MenuUpdate, MenuListResponse, MenuListApiResponse, MenuBriefResponse
from app.schemas.response import ApiResponse

router = APIRouter()


class MenuScope:
    LIST   = "menu:list"
    CREATE = "menu:create"
    UPDATE = "menu:update"
    DELETE = "menu:delete"


@router.get("", response_model=MenuListApiResponse, summary="菜单列表")
async def list_menus(
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.LIST])],
):
    result = await db.execute(select(Menu).order_by(Menu.sort_order, Menu.id))
    menus = result.scalars().all()
    data = MenuListResponse(
        items=[
            {
                "id": m.id, "code": m.code, "name": m.name,
                "icon": m.icon, "path": m.path,
                "parent_id": m.parent_id, "sort_order": m.sort_order,
            }
            for m in menus
        ],
        total=len(menus),
    )
    return ApiResponse.ok(data=data)


@router.post("", response_model=MenuBriefResponse, status_code=201, summary="创建菜单")
async def create_menu(
    body: MenuCreate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.CREATE])],
):
    if (await db.execute(select(Menu).where(Menu.code == body.code))).scalars().first():
        raise BusinessException(ErrorCode.MENU_CODE_EXISTS, "菜单编码已存在")
    menu = Menu(
        code=body.code, name=body.name, icon=body.icon,
        path=body.path, parent_id=body.parent_id, sort_order=body.sort_order,
    )
    db.add(menu)
    await db.commit()
    await db.refresh(menu)
    return ApiResponse.ok(data=menu, message="创建成功")


@router.put("/{menu_id}", response_model=MenuBriefResponse, summary="更新菜单")
async def update_menu(
    menu_id: int,
    body: MenuUpdate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.UPDATE])],
):
    result = await db.execute(select(Menu).where(Menu.id == menu_id))
    menu = result.scalars().first()
    if not menu:
        raise BusinessException(ErrorCode.MENU_NOT_FOUND, f"菜单不存在: {menu_id}")
    if body.name is not None:
        menu.name = body.name
    if body.icon is not None:
        menu.icon = body.icon
    if body.path is not None:
        menu.path = body.path
    if body.parent_id is not None:
        menu.parent_id = body.parent_id
    if body.sort_order is not None:
        menu.sort_order = body.sort_order
    await db.commit()
    return ApiResponse.ok(data=menu, message="更新成功")


@router.delete("/{menu_id}", response_model=ApiResponse, summary="删除菜单")
async def delete_menu(
    menu_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.DELETE])],
):
    result = await db.execute(select(Menu).where(Menu.id == menu_id))
    menu = result.scalars().first()
    if not menu:
        raise BusinessException(ErrorCode.MENU_NOT_FOUND, f"菜单不存在: {menu_id}")
    await db.delete(menu)
    await db.commit()
    return ApiResponse.ok(message="删除成功")

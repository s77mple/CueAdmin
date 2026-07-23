"""菜单管理 API"""

from typing import Annotated

from fastapi import APIRouter, Security
from sqlalchemy import select

from app.core.database import DbSession
from app.core.dependencies import get_current_user
from app.models import Menu, User
from app.schemas.menu import MenuCreate, MenuUpdate
from app.core.exceptions import NotFoundException, ConflictException

router = APIRouter()


# ---- 权限码常量 ----
class MenuScope:
    LIST   = "menu:list"
    CREATE = "menu:create"
    UPDATE = "menu:update"
    DELETE = "menu:delete"


@router.get("", summary="菜单列表")
async def list_menus(
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.LIST])],
):
    result = await db.execute(select(Menu).order_by(Menu.code.asc()))
    menus = result.scalars().all()
    return {
        "items": [
            {"id": m.id, "code": m.code, "name": m.name, "icon": m.icon, "path": m.path}
            for m in menus
        ],
        "total": len(menus),
    }


@router.post("", status_code=201, summary="创建菜单")
async def create_menu(
    body: MenuCreate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.CREATE])],
):
    if (await db.execute(select(Menu).where(Menu.code == body.code))).scalars().first():
        raise ConflictException("菜单编码已存在")
    menu = Menu(code=body.code, name=body.name, icon=body.icon, path=body.path)
    db.add(menu)
    await db.commit()
    await db.refresh(menu)
    return {"id": menu.id, "code": menu.code, "name": menu.name}


@router.put("/{menu_id}", summary="更新菜单")
async def update_menu(
    menu_id: int,
    body: MenuUpdate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.UPDATE])],
):
    result = await db.execute(select(Menu).where(Menu.id == menu_id))
    menu = result.scalars().first()
    if not menu:
        raise NotFoundException("Menu", menu_id)
    if body.name is not None:
        menu.name = body.name
    if body.icon is not None:
        menu.icon = body.icon
    if body.path is not None:
        menu.path = body.path
    await db.commit()
    return {"id": menu.id, "code": menu.code}


@router.delete("/{menu_id}", summary="删除菜单")
async def delete_menu(
    menu_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.DELETE])],
):
    result = await db.execute(select(Menu).where(Menu.id == menu_id))
    menu = result.scalars().first()
    if not menu:
        raise NotFoundException("Menu", menu_id)
    await db.delete(menu)
    await db.commit()
    return {"message": "删除成功"}

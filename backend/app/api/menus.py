"""菜单管理 API"""

from typing import Annotated

from fastapi import APIRouter, Security
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


async def _would_create_cycle(db: AsyncSession, menu_id: int, new_parent_id: int) -> bool:
    """检查将 menu_id 的父级设为 new_parent_id 是否会产生循环引用。
    沿父链向上遍历：如果最终到达 menu_id 自己，则存在循环。
    """
    current_id = new_parent_id
    visited: set[int] = set()
    while current_id is not None:
        if current_id == menu_id:
            return True
        if current_id in visited:
            # 数据库已有坏数据（循环），终止遍历
            from app.core.logger import logger
            logger.warning(f"菜单表存在循环引用: menu_id={menu_id} 的祖先链中出现重复节点 {current_id}")
            break
        visited.add(current_id)
        result = await db.execute(
            select(Menu.parent_id).where(Menu.id == current_id)
        )
        row = result.first()
        current_id = row[0] if row else None
    return False


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
    if body.parent_id is not None:
        parent = (await db.execute(select(Menu).where(Menu.id == body.parent_id))).scalars().first()
        if not parent:
            raise BusinessException(ErrorCode.MENU_NOT_FOUND, f"父菜单不存在: {body.parent_id}")
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
    result = await db.execute(
        select(Menu).where(Menu.id == menu_id).with_for_update()
    )
    menu = result.scalars().first()
    if not menu:
        raise BusinessException(ErrorCode.MENU_NOT_FOUND, f"菜单不存在: {menu_id}")
    if body.name is not None:
        menu.name = body.name
    if body.icon is not None:
        menu.icon = body.icon
    if body.path is not None:
        menu.path = body.path
    if "parent_id" in body.model_dump(exclude_unset=True):
        new_parent_id = body.parent_id
        if new_parent_id is not None:
            if new_parent_id == menu_id:
                raise BusinessException(ErrorCode.CONFLICT, "菜单不能将自己设为父菜单")
            parent = (await db.execute(select(Menu).where(Menu.id == new_parent_id))).scalars().first()
            if not parent:
                raise BusinessException(ErrorCode.MENU_NOT_FOUND, f"父菜单不存在: {new_parent_id}")
            # 检查循环引用：新父菜单的祖先链中不能包含自己
            if await _would_create_cycle(db, menu_id, new_parent_id):
                raise BusinessException(ErrorCode.CONFLICT, "不能将菜单设置为自己的子孙菜单")
        menu.parent_id = new_parent_id
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
    # 检查子菜单
    children = (await db.execute(
        select(Menu).where(Menu.parent_id == menu_id)
    )).scalars().all()
    child_info = None
    if children:
        child_names = [c.name for c in children]
        child_info = {"count": len(children), "children": child_names}
        for child in children:
            child.parent_id = None
    await db.delete(menu)
    await db.commit()
    if child_info:
        return ApiResponse.ok(
            message=f"已删除，{child_info['count']} 个子菜单已变为顶级菜单",
            data=child_info,
        )
    return ApiResponse.ok(message="删除成功")

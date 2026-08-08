"""
菜单管理 API — 树形结构 CRUD。

菜单的特殊处理：
  - parent_id 循环检测：不能把菜单设为它自己的子孙
    （与部门管理完全相同的模式）
  - 删除菜单 → 子菜单自动变顶级（SET NULL）
  - 删除后返回影响了多少子菜单
"""

from typing import Annotated

from fastapi import APIRouter, Security
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import DbSession
from app.core.dependencies import get_current_user
from app.core.exceptions import BusinessException, ErrorCode
from app.models import Menu, User
from app.schemas.menu import MenuCreate, MenuUpdate, MenuPatch, MenuListResponse, MenuListApiResponse, MenuBriefResponse
from app.schemas.response import ApiResponse

router = APIRouter()


class MenuScope:
    LIST   = "menu:list"
    CREATE = "menu:create"
    UPDATE = "menu:update"
    DELETE = "menu:delete"


# ============================================================
# 1. 循环检测 — 防止 parent_id 形成死循环
# ============================================================

async def _would_create_cycle(db: AsyncSession, menu_id: int, new_parent_id: int) -> bool:
    """#1 检查将 menu_id 的父级设为 new_parent_id 是否会形成循环。

    做法：从 new_parent_id 出发沿 parent_id 链向上爬，
    如果爬到 menu_id 自己 → 有循环，拒绝操作。

    例：
      菜单 A(id=1) 的父级是 B(id=2)
      如果把 B 的父级设为 A → 沿链: A→B→A → 循环！
      如果把 A 的父级设为 null → 不会循环
    """
    current_id = new_parent_id
    visited: set[int] = set()  # 防止数据库已有坏数据导致无限循环
    while current_id is not None:
        if current_id == menu_id:
            return True  # 发现循环
        if current_id in visited:
            # 数据库有坏数据（已存在循环），终止遍历
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


# ============================================================
# 2. GET /menus — 菜单列表
# ============================================================

@router.get("", response_model=MenuListApiResponse, summary="菜单列表")
async def list_menus(
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.LIST])],
):
    """#2 返回全部菜单（扁平列表，前端用 parent_id 转树）。"""
    result = await db.execute(select(Menu).order_by(Menu.sort_order, Menu.id))
    menus = result.scalars().all()
    data = MenuListResponse(
        items=[
            {
                "id": m.id, "code": m.code, "name": m.name,
                "icon": m.icon, "path": m.path, "component": m.component,
                "parent_id": m.parent_id, "sort_order": m.sort_order,
            }
            for m in menus
        ],
        total=len(menus),
    )
    return ApiResponse.ok(data=data)


# ============================================================
# 3. POST /menus — 创建菜单
# ============================================================

@router.post("", response_model=MenuBriefResponse, status_code=201, summary="创建菜单")
async def create_menu(
    body: MenuCreate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.CREATE])],
):
    """#3 创建菜单 — 验证父菜单存在 + 双重唯一性保护。"""
    if (await db.execute(select(Menu).where(Menu.code == body.code))).scalars().first():
        raise BusinessException(ErrorCode.MENU_CODE_EXISTS, "菜单编码已存在")

    # 验证父菜单存在
    if body.parent_id is not None:
        parent = (await db.execute(select(Menu).where(Menu.id == body.parent_id))).scalars().first()
        if not parent:
            raise BusinessException(ErrorCode.MENU_NOT_FOUND, f"父菜单不存在: {body.parent_id}")

    menu = Menu(
        code=body.code, name=body.name, icon=body.icon,
        path=body.path, component=body.component,
        parent_id=body.parent_id, sort_order=body.sort_order,
    )
    db.add(menu)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise BusinessException(ErrorCode.MENU_CODE_EXISTS, "菜单编码已存在")
    await db.refresh(menu)
    return ApiResponse.ok(data=menu, message="创建成功")


# ============================================================
# 4. PUT /menus/{menu_id} — 全量更新
# ============================================================

@router.put("/{menu_id}", response_model=MenuBriefResponse, summary="全量更新菜单")
async def update_menu(
    menu_id: int,
    body: MenuUpdate,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.UPDATE])],
):
    """#4 PUT 全量更新 — 包含循环检测。"""
    result = await db.execute(
        select(Menu).where(Menu.id == menu_id).with_for_update()
    )
    menu = result.scalars().first()
    if not menu:
        raise BusinessException(ErrorCode.MENU_NOT_FOUND, f"菜单不存在: {menu_id}")

    # 校验父菜单 + 循环检测
    if body.parent_id is not None:
        if body.parent_id == menu_id:
            raise BusinessException(ErrorCode.CONFLICT, "菜单不能将自己设为父菜单")
        parent = (await db.execute(select(Menu).where(Menu.id == body.parent_id))).scalars().first()
        if not parent:
            raise BusinessException(ErrorCode.MENU_NOT_FOUND, f"父菜单不存在: {body.parent_id}")
        if await _would_create_cycle(db, menu_id, body.parent_id):
            raise BusinessException(ErrorCode.CONFLICT, "不能将菜单设置为自己的子孙菜单")

    # 全量覆盖
    menu.name = body.name
    menu.icon = body.icon
    menu.path = body.path
    menu.component = body.component
    menu.parent_id = body.parent_id
    menu.sort_order = body.sort_order

    await db.commit()
    return ApiResponse.ok(data=menu, message="更新成功")


# ============================================================
# 5. PATCH /menus/{menu_id} — 部分更新
# ============================================================

@router.patch("/{menu_id}", response_model=MenuBriefResponse, summary="部分更新菜单")
async def patch_menu(
    menu_id: int,
    body: MenuPatch,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.UPDATE])],
):
    """#5 PATCH 部分更新 — 传什么改什么。"""
    result = await db.execute(
        select(Menu).where(Menu.id == menu_id).with_for_update()
    )
    menu = result.scalars().first()
    if not menu:
        raise BusinessException(ErrorCode.MENU_NOT_FOUND, f"菜单不存在: {menu_id}")

    data = body.model_dump(exclude_unset=True)

    if "name" in data:
        if data["name"] is None:
            raise BusinessException(ErrorCode.VALIDATION_ERROR, "name 不能为 null")
        menu.name = data["name"]
    if "icon" in data:
        menu.icon = data["icon"]        # null = 清除图标
    if "path" in data:
        menu.path = data["path"]        # null = 清除路径
    if "component" in data:
        menu.component = data["component"]  # null = 变成目录菜单

    if "parent_id" in data:
        new_parent_id = data["parent_id"]
        if new_parent_id is not None:
            if new_parent_id == menu_id:
                raise BusinessException(ErrorCode.CONFLICT, "菜单不能将自己设为父菜单")
            parent = (await db.execute(select(Menu).where(Menu.id == new_parent_id))).scalars().first()
            if not parent:
                raise BusinessException(ErrorCode.MENU_NOT_FOUND, f"父菜单不存在: {new_parent_id}")
            if await _would_create_cycle(db, menu_id, new_parent_id):
                raise BusinessException(ErrorCode.CONFLICT, "不能将菜单设置为自己的子孙菜单")
        menu.parent_id = new_parent_id

    if "sort_order" in data:
        menu.sort_order = data["sort_order"]

    await db.commit()
    return ApiResponse.ok(data=menu, message="更新成功")


# ============================================================
# 6. DELETE /menus/{menu_id} — 删除菜单
# ============================================================

@router.delete("/{menu_id}", response_model=ApiResponse, summary="删除菜单")
async def delete_menu(
    menu_id: int,
    db: DbSession,
    user: Annotated[User, Security(get_current_user, scopes=[MenuScope.DELETE])],
):
    """#6 删除菜单 — 子菜单自动变顶级。

    不递归删除子菜单（安全策略）：
      删"系统管理" → 子菜单"用户管理"自动变为顶级菜单
      管理员可以逐个处理变顶级的菜单，不会误删。
    """
    result = await db.execute(
        select(Menu).where(Menu.id == menu_id).with_for_update()
    )
    menu = result.scalars().first()
    if not menu:
        raise BusinessException(ErrorCode.MENU_NOT_FOUND, f"菜单不存在: {menu_id}")

    # 子菜单变顶级（SET NULL）
    children = (await db.execute(
        select(Menu).where(Menu.parent_id == menu_id).with_for_update()
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

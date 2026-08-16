"""
菜单公共服务 — 用户菜单收集 & 路由树构建。

本模块提供两个核心函数，被 login、/me、/routes 三个接口共用：

  collect_user_menus() → 扁平菜单列表（含父级自动补全）
  build_routes()       → 扁平列表 → Pure Admin 路由树

抽取原因：
  auth_service.py、auth.py（/me 端点）、routes.py 三处原本有 ~60 行
  几乎完全相同的菜单收集+父级补全逻辑，任何修改需要同步三处。
  现在统一收口到这里，三处调用方各只需一行调用。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Menu
from app.core.logger import logger
from app.core.exceptions import BusinessException, ErrorCode


async def collect_user_menus(session: AsyncSession, user: User) -> list[dict]:
    """收集用户有权限看到的菜单（扁平列表，含自动补全的父级菜单）。

    处理三种情况：
      admin 角色 → 返回全部菜单，不补全（全量查询已包含所有父子关系）
      普通角色   → 返回角色绑定的菜单 + 自动补全缺失的父级菜单
      无角色     → 返回空列表

    每条菜单数据的字段：
      id, code, name, icon, path, component, parent_id, sort_order
    """

    # ---- admin 拥有全部菜单 ----
    if any(role.code == "admin" for role in user.roles):
        stmt = select(Menu).order_by(Menu.sort_order, Menu.id)
        result = await session.execute(stmt)
        all_menus = result.scalars().all()
        menus = [
            _menu_to_dict(m) for m in all_menus
        ]
    else:
        seen: set[str] = set()       # 用 code 去重
        seen_ids: set[int] = set()   # 用 id 追踪（供父级补全用）
        menus: list[dict] = []

        # 收集角色直接绑定的菜单
        for role in user.roles:
            for m in role.menus:
                if m.code not in seen:
                    seen.add(m.code)
                    seen_ids.add(m.id)
                    menus.append(_menu_to_dict(m))

        # 自动补全缺失的父级菜单
        # 场景：角色分配了 /users/index 但没分配父菜单 /users
        # 前端树形菜单需要完整的父子链才能正确渲染
        while True:
            missing = {
                m["parent_id"]
                for m in menus
                if m["parent_id"] is not None and m["parent_id"] not in seen_ids
            }
            if not missing:
                break

            stmt = select(Menu).where(Menu.id.in_(missing))
            result = await session.execute(stmt)
            parents = result.scalars().all()
            if not parents:
                break  # 孤立引用（parent_id 指向不存在的记录）

            for p in parents:
                if p.id not in seen_ids:
                    seen_ids.add(p.id)
                    menus.append(_menu_to_dict(p))
                    logger.debug(
                        "自动补全父级菜单: id=%d code=%s name=%s", p.id, p.code, p.name
                    )

    menus.sort(key=lambda m: m["sort_order"])
    return menus


def _menu_to_dict(m: Menu) -> dict:
    """ORM 对象转 dict — 统一字段集合，防止各处手写不一致。"""
    return {
        "id": m.id,
        "code": m.code,
        "name": m.name,
        "icon": m.icon,
        "path": m.path,
        "component": m.component,
        "parent_id": m.parent_id,
        "sort_order": m.sort_order,
    }


# ============================================================
# 路由树构建 — 扁平菜单 → Pure Admin 嵌套路由 JSON
# ============================================================

def build_routes(menus: list[dict]) -> list[dict]:
    """将扁平菜单列表转成 Pure Admin 格式的嵌套路由树。

    输入：[{id, code, name, icon, path, component, parent_id, sort_order}, ...]
    输出：[{path, name, redirect?, component?, meta, children?}, ...]

    遇到 parent_id 循环引用时跳过问题节点（graceful degradation），
    不会因为一个坏数据导致整个路由接口崩溃。
    """

    # ---- 按 parent_id 构建树 ----
    menu_map: dict[int, dict] = {}
    top_nodes: list[dict] = []

    for m in menus:
        node = {
            "id": m["id"],
            "code": m.get("code", ""),
            "path": m.get("path") or "",
            "name": m.get("name", ""),
            "icon": m.get("icon"),
            "component": m.get("component"),
            "parent_id": m.get("parent_id"),
            "sort_order": m.get("sort_order", 0),
            "children": [],
        }
        menu_map[m["id"]] = node

    # parent_id 在 menu_map 中 → 子节点
    # parent_id 不在 menu_map 中 → 顶级节点
    for node in menu_map.values():
        pid = node.get("parent_id")
        if pid is not None and pid in menu_map:
            menu_map[pid]["children"].append(node)
        else:
            top_nodes.append(node)

    # ---- 递归排序 ----
    def sort_children(nodes: list[dict]):
        nodes.sort(key=lambda n: n.get("sort_order", 0))
        for n in nodes:
            if n["children"]:
                sort_children(n["children"])

    sort_children(top_nodes)

    # ---- 转 Pure Admin 路由格式 ----
    def to_route(node: dict, seen: set | None = None) -> dict | None:
        """递归转换单个节点。

        遇到循环引用时不抛异常，而是记录警告并跳过该节点，
        确保其他正常菜单仍然能渲染。
        """
        if seen is None:
            seen = set()
        node_id = node["id"]

        if node_id in seen:
            logger.warning(
                "菜单 parent_id 存在循环引用，已跳过该节点: id=%d code=%s name=%s",
                node_id, node.get("code"), node.get("name")
            )
            return None  # graceful degradation：跳过而非崩溃

        seen.add(node_id)

        # 递归处理子节点（跳过返回 None 的循环节点）
        children_routes = []
        if node["children"]:
            for c in node["children"]:
                child_route = to_route(c, seen.copy())
                if child_route is not None:
                    children_routes.append(child_route)

        route: dict = {
            "path": node["path"] or "",
            "name": node["code"],
            "meta": {
                "title": node["name"],
                "rank": node.get("sort_order", 0),
            },
        }

        if node.get("icon"):
            route["meta"]["icon"] = node["icon"]

        if children_routes:
            for c in children_routes:
                c["meta"]["showParent"] = True
            route["children"] = children_routes
            route["redirect"] = children_routes[0]["path"]
        else:
            if node.get("component"):
                route["component"] = node["component"]
            else:
                logger.warning(
                    "菜单 [%s] 为叶子节点但缺少 component，前端可能无法渲染",
                    node.get("code")
                )

        return route

    # 构建路由列表，过滤掉返回 None 的节点
    routes: list[dict] = []
    for n in top_nodes:
        r = to_route(n)
        if r is not None:
            routes.append(r)

    return routes


# ============================================================
# MenuService — 菜单 CRUD 业务逻辑
# ============================================================

from sqlalchemy.exc import IntegrityError
from app.models import Menu
from app.core.exceptions import BusinessException, ErrorCode


class MenuService:
    """菜单管理 CRUD 业务逻辑。

    与上方的 collect_user_menus / build_routes 不同：
      - collect_user_menus / build_routes 是跨模块工具函数（被 login、/me、/routes 共用）
      - MenuService 是菜单的增删改查业务逻辑（被 /menus 端点使用）
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # ============================================================
    # 查询
    # ============================================================

    async def list_menus(self) -> list[Menu]:
        """返回全部菜单（扁平列表，前端用 parent_id 转树）。"""
        result = await self.session.execute(
            select(Menu).order_by(Menu.sort_order, Menu.id).limit(500)
        )
        return list(result.scalars().all())

    async def get_menu_for_update(self, menu_id: int) -> Menu:
        """带行级锁获取菜单。"""
        result = await self.session.execute(
            select(Menu).where(Menu.id == menu_id).with_for_update()
        )
        menu = result.scalars().first()
        if not menu:
            raise BusinessException(ErrorCode.MENU_NOT_FOUND, f"菜单不存在: {menu_id}")
        return menu

    # ============================================================
    # 创建
    # ============================================================

    async def create_menu(self, body) -> Menu:
        """创建菜单 — 验证父菜单 + 双重唯一性保护。"""
        if (await self.session.execute(select(Menu).where(Menu.code == body.code))).scalars().first():
            raise BusinessException(ErrorCode.MENU_CODE_EXISTS, "菜单编码已存在")

        if body.parent_id is not None:
            parent = (await self.session.execute(select(Menu).where(Menu.id == body.parent_id))).scalars().first()
            if not parent:
                raise BusinessException(ErrorCode.MENU_NOT_FOUND, f"父菜单不存在: {body.parent_id}")

        menu = Menu(
            code=body.code, name=body.name, icon=body.icon,
            path=body.path, component=body.component,
            parent_id=body.parent_id, sort_order=body.sort_order,
        )
        self.session.add(menu)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise BusinessException(ErrorCode.MENU_CODE_EXISTS, "菜单编码已存在")
        await self.session.refresh(menu)
        return menu

    # ============================================================
    # 全量更新
    # ============================================================

    async def update_menu(self, menu_id: int, body) -> Menu:
        """PUT 全量更新 — 包含循环检测。"""
        menu = await self.get_menu_for_update(menu_id)

        if body.parent_id is not None:
            await self._validate_parent(menu_id, body.parent_id)

        menu.name = body.name
        menu.icon = body.icon
        menu.path = body.path
        menu.component = body.component
        menu.parent_id = body.parent_id
        menu.sort_order = body.sort_order

        await self.session.commit()
        return menu

    # ============================================================
    # 删除
    # ============================================================

    async def delete_menu(self, menu_id: int) -> dict:
        """删除菜单 — 子菜单自动变顶级。"""
        menu = await self.get_menu_for_update(menu_id)

        # 子菜单变顶级
        children = (await self.session.execute(
            select(Menu).where(Menu.parent_id == menu_id).with_for_update()
        )).scalars().all()
        child_info = None
        if children:
            child_names = [c.name for c in children]
            child_info = {"count": len(children), "children": child_names}
            for child in children:
                child.parent_id = None

        await self.session.delete(menu)
        await self.session.commit()

        if child_info:
            return {
                "message": f"已删除，{child_info['count']} 个子菜单已变为顶级菜单",
                "child_info": child_info,
            }
        return {"message": "删除成功"}

    # ============================================================
    # 私有 — 循环检测
    # ============================================================

    async def _validate_parent(self, menu_id: int, new_parent_id: int):
        """校验父菜单存在 + 检测循环引用。"""
        if new_parent_id == menu_id:
            raise BusinessException(ErrorCode.CONFLICT, "菜单不能将自己设为父菜单")

        parent = (await self.session.execute(select(Menu).where(Menu.id == new_parent_id))).scalars().first()
        if not parent:
            raise BusinessException(ErrorCode.MENU_NOT_FOUND, f"父菜单不存在: {new_parent_id}")

        if await self._would_create_cycle(menu_id, new_parent_id):
            raise BusinessException(ErrorCode.CONFLICT, "不能将菜单设置为自己的子孙菜单")

    async def _would_create_cycle(self, menu_id: int, new_parent_id: int) -> bool:
        """检查 parent_id 变更是否会形成循环。"""
        current_id = new_parent_id
        visited: set[int] = set()
        while current_id is not None:
            if current_id == menu_id:
                return True
            if current_id in visited:
                logger.warning(f"菜单表存在循环引用: menu_id={menu_id} 的祖先链中出现重复节点 {current_id}")
                break
            visited.add(current_id)
            result = await self.session.execute(
                select(Menu.parent_id).where(Menu.id == current_id)
            )
            row = result.first()
            current_id = row[0] if row else None
        return False

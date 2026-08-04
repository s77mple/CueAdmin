"""动态路由 API — 返回 Pure Admin 格式的路由数据，供前端 initRouter 使用。"""

from typing import Annotated

from fastapi import APIRouter, Security
from sqlalchemy import select

from app.core.database import DbSession
from app.core.dependencies import get_current_user
from app.models import User, Menu
from app.schemas.response import ApiResponse

router = APIRouter()


def _build_routes(menus: list) -> list[dict]:
    """将扁平菜单列表转成 Pure Admin 动态路由树。

    Pure Admin 期望的格式::

        {
            "path": "/users",
            "name": "Users",
            "redirect": "/users/index",
            "meta": {"icon": "...", "title": "...", "rank": 2},
            "children": [
                {
                    "path": "/users/index",
                    "name": "UserList",
                    "component": "system/users/index",
                    "meta": {"title": "用户管理"}
                }
            ]
        }
    """
    # 按 parent_id 分组，建立树
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

    # 构建父子关系
    for node in menu_map.values():
        pid = node.get("parent_id")
        if pid and pid in menu_map:
            menu_map[pid]["children"].append(node)
        else:
            top_nodes.append(node)

    # 按 sort_order 排序
    def sort_children(nodes: list[dict]):
        nodes.sort(key=lambda n: n.get("sort_order", 0))
        for n in nodes:
            if n["children"]:
                sort_children(n["children"])

    sort_children(top_nodes)

    # 转换为 Pure Admin 格式
    def to_route(node: dict) -> dict:
        children_routes = [to_route(c) for c in node["children"]] if node["children"] else []

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
            # 子路由加 showParent，防止 Pure Admin 把单子父菜单折叠（父标题被隐藏只显示子标题）
            for c in children_routes:
                c["meta"]["showParent"] = True
            route["children"] = children_routes
            # redirect 默认取第一个子级的 path
            route["redirect"] = children_routes[0]["path"]
        else:
            # 叶子节点：必须指定 component，否则 path 匹配不到 Vue 文件
            if node.get("component"):
                route["component"] = node["component"]

        return route

    return [to_route(n) for n in top_nodes]


@router.get("", response_model=ApiResponse[list], summary="获取当前用户动态路由")
async def get_routes(
    db: DbSession,
    user: Annotated[User, Security(get_current_user)],
):
    """返回当前用户角色的菜单，格式适配 Pure Admin 动态路由。"""
    # 系统角色（admin）拥有全部菜单权限
    if any(role.is_system for role in user.roles):
        stmt = select(Menu).order_by(Menu.sort_order, Menu.id)
        result = await db.execute(stmt)
        all_menus = result.scalars().all()
        menus = [
            {
                "id": m.id, "code": m.code, "name": m.name,
                "icon": m.icon, "path": m.path, "component": m.component,
                "parent_id": m.parent_id, "sort_order": m.sort_order,
            }
            for m in all_menus
        ]
    else:
        seen: set[int] = set()
        menus: list[dict] = []
        for role in user.roles:
            for m in role.menus:
                if m.id not in seen:
                    seen.add(m.id)
                    menus.append({
                        "id": m.id, "code": m.code, "name": m.name,
                        "icon": m.icon, "path": m.path, "component": m.component,
                        "parent_id": m.parent_id, "sort_order": m.sort_order,
                    })
        menus.sort(key=lambda m: m["sort_order"])

    routes = _build_routes(menus)
    return ApiResponse.ok(data=routes)

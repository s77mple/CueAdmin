"""
动态路由 API — 返回 Pure Admin 格式的菜单路由数据。

这是前端 initRouter() 的数据源，整个前端导航菜单由这个接口决定。

前端动态路由生成流程：
  #1 用户登录成功 → 拿到 token + menus
    或：刷新页面 → router.beforeEach → getMe() → 拿到 menus
  #2 getAsyncRoutes() 调用 GET /api/v1/routes
  #3 后端返回 Pure Admin 格式的路由 JSON:
     [
       {
         "path": "/users",
         "name": "users",
         "redirect": "/users/index",
         "meta": { "icon": "...", "title": "用户管理", "rank": 2 },
         "children": [
           {
             "path": "/users/index",
             "name": "users_index",
             "component": "system/users/index",
             "meta": { "title": "用户列表", "showParent": true }
           }
         ]
       }
     ]
  #4 前端 addAsyncRoutes() 匹配 component 字符串到 Vue 文件
  #5 router.addRoute() 动态注册

Pure Admin 路由格式说明：
  - 目录菜单（有 children）：有 redirect，无 component
  - 叶子菜单：有 component，无 redirect
  - meta.rank → 侧边栏排序（越小越前）
  - meta.showParent → 让单子父菜单不折叠（父标题不会被隐藏）
"""

from typing import Annotated

from fastapi import APIRouter, Security
from sqlalchemy import select

from app.core.database import DbSession
from app.core.dependencies import get_current_user
from app.core.exceptions import BusinessException, ErrorCode
from app.core.logger import logger
from app.models import User, Menu
from app.schemas.response import ApiResponse

router = APIRouter()


# ============================================================
# 1. 核心函数 — 扁平菜单列表 → Pure Admin 路由树
# ============================================================

def _build_routes(menus: list) -> list[dict]:
    """#1 将扁平菜单列表转成 Pure Admin 格式的路由树。

    输入：[{id, code, name, icon, path, component, parent_id, sort_order}, ...]
    输出：[{path, name, redirect?, component?, meta, children?}, ...]

    步骤：
      a. 按 parent_id 分组建立父子关系（result = 树的数组）
      b. 按 sort_order 递归排序
      c. 转为 Pure Admin 路由格式（带循环检测）
    """

    # ---- #1a 按 parent_id 构建树 ----
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

    # parent_id 在 menu_map 中 → 是某节点的子节点
    # parent_id 不在 menu_map 中 → 顶级节点
    for node in menu_map.values():
        pid = node.get("parent_id")
        if pid is not None and pid in menu_map:
            menu_map[pid]["children"].append(node)
        else:
            top_nodes.append(node)

    # ---- #1b 递归排序 ----
    def sort_children(nodes: list[dict]):
        nodes.sort(key=lambda n: n.get("sort_order", 0))
        for n in nodes:
            if n["children"]:
                sort_children(n["children"])

    sort_children(top_nodes)

    # ---- #1c 转 Pure Admin 路由格式 ----
    def to_route(node: dict, seen: set | None = None) -> dict:
        """递归转换单个节点为 Pure Admin 路由格式。

        seen 集合用于循环检测（防御数据异常）。
        seen.copy() 确保兄弟节点之间不互相干扰。
        """
        if seen is None:
            seen = set()
        node_id = node["id"]
        if node_id in seen:
            raise BusinessException(
                ErrorCode.CONFLICT,
                f"菜单 parent_id 存在循环引用: id={node_id} code={node.get('code')} name={node.get('name')}"
            )
        seen.add(node_id)

        # 递归处理子节点
        children_routes = [to_route(c, seen.copy()) for c in node["children"]] if node["children"] else []

        # 构建路由对象
        route: dict = {
            "path": node["path"] or "",
            "name": node["code"],  # 用菜单 code 作为路由 name（Pure Admin 要求 name 唯一）
            "meta": {
                "title": node["name"],
                "rank": node.get("sort_order", 0),
            },
        }

        if node.get("icon"):
            route["meta"]["icon"] = node["icon"]

        if children_routes:
            # 父菜单 = 目录路由
            # showParent 防止 Pure Admin 把单子父菜单折叠（只显示子标题，隐藏父标题）
            for c in children_routes:
                c["meta"]["showParent"] = True
            route["children"] = children_routes
            route["redirect"] = children_routes[0]["path"]  # 点击父菜单 → 自动跳到第一个子菜单
        else:
            # 叶子菜单 = 页面路由
            if node.get("component"):
                route["component"] = node["component"]
            else:
                logger.warning("菜单 [{}] 为叶子节点但缺少 component，前端可能无法渲染", node.get("code"))

        return route

    return [to_route(n) for n in top_nodes]


# ============================================================
# 2. GET /routes — 获取当前用户的动态路由
# ============================================================

@router.get("", response_model=ApiResponse[list], summary="获取当前用户动态路由")
async def get_routes(
    db: DbSession,
    user: Annotated[User, Security(get_current_user)],  # 仅认证不鉴权（不需要 scope）
):
    """#2 返回当前用户有权限看到的菜单，格式适配 Pure Admin。

    前端调用时机：
      - 登录成功后 → getAsyncRoutes()
      - 刷新页面后 → router.beforeEach 检测到无路由数据 → getMe() → getAsyncRoutes()
    """
    # admin 角色拥有全部菜单
    if any(role.code == "admin" for role in user.roles):
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

        # 补全缺失的父级菜单
        # 场景：角色有 /users/index 但没 /users → 父级缺失 → 树断裂
        # 自动补全：查 parent_id 不在已有菜单中的，从 DB 拉回来
        while True:
            missing = {
                m["parent_id"]
                for m in menus
                if m["parent_id"] is not None and m["parent_id"] not in seen
            }
            if not missing:
                break
            stmt = select(Menu).where(Menu.id.in_(missing))
            result = await db.execute(stmt)
            parents = result.scalars().all()
            if not parents:
                break
            for p in parents:
                if p.id not in seen:
                    seen.add(p.id)
                    menus.append({
                        "id": p.id, "code": p.code, "name": p.name,
                        "icon": p.icon, "path": p.path, "component": p.component,
                        "parent_id": p.parent_id, "sort_order": p.sort_order,
                    })
                    logger.debug(
                        "自动补全父级菜单: id=%d code=%s name=%s", p.id, p.code, p.name
                    )

        menus.sort(key=lambda m: m["sort_order"])

    routes = _build_routes(menus)
    return ApiResponse.ok(data=routes)

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

from app.core.database import DbSession
from app.core.dependencies import get_current_user
from app.models import User
from app.schemas.response import ApiResponse
from app.services.menu_service import collect_user_menus, build_routes

router = APIRouter()


# ============================================================
# GET /routes — 获取当前用户的动态路由
# ============================================================

@router.get("", response_model=ApiResponse[list], summary="获取当前用户动态路由")
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

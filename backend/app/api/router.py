"""路由汇总 — 把所有子模块的路由收集到一个总路由。

所有 API 统一挂载在 /api/v1 前缀下（main.py 设置）。

最终 URL 结构：
  POST   /api/v1/auth/login            → auth.router
  POST   /api/v1/auth/logout
  GET    /api/v1/auth/me
  PUT    /api/v1/auth/profile
  GET    /api/v1/users                 → users.router
  GET    /api/v1/users/{id}
  POST   /api/v1/users
  PUT    /api/v1/users/{id}
  PATCH  /api/v1/users/{id}
  DELETE /api/v1/users/{id}
  ...（roles/menus/permissions/departments/routes 同理）
"""

from fastapi import APIRouter

from app.api import auth, users, roles, menus, permissions, departments, me

api_router = APIRouter()

# 各模块路由 + 前缀 + OpenAPI 文档分组标签
api_router.include_router(auth.router,        prefix="/auth",        tags=["认证"])
api_router.include_router(users.router,       prefix="/users",       tags=["用户管理"])
api_router.include_router(roles.router,       prefix="/roles",       tags=["角色管理"])
api_router.include_router(menus.router,       prefix="/menus",       tags=["菜单管理"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["权限管理"])
api_router.include_router(me.routes_router, prefix="/routes", tags=["动态路由"])
api_router.include_router(departments.router, prefix="/departments", tags=["部门管理"])

"""路由汇总。所有 API 挂载在 /api/v1 前缀下。"""

from fastapi import APIRouter

from app.api import auth, users, roles, menus, permissions, routes

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["认证"])
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])
api_router.include_router(roles.router, prefix="/roles", tags=["角色管理"])
api_router.include_router(menus.router, prefix="/menus", tags=["菜单管理"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["权限管理"])
api_router.include_router(routes.router, prefix="/routes", tags=["动态路由"])

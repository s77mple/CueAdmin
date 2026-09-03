"""路由汇总 — 把所有子模块的路由收集到一个总路由。

URL 三层结构（从外到内）：

  /api/v1         版本前缀      —— main.py 挂载时设置（换 v2 只改这一层）
  /system         模块组前缀    —— 本文件的 system_router 设置（系统管理那批）
  /users /roles   资源前缀      —— 各模块自己的 APIRouter 里声明

换 v2 的做法：
  1. 复制 app/system/api/v1/ 整个目录为 v2/
  2. main.py 里再 app.include_router(v2_router, prefix="/api/v2")
  /system 分组结构不变，各模块前缀不变，只要这两步。

登录（/auth）和动态路由（/routes）不属于"系统管理"，
直接挂在 v1_router 下、不带 /system —— 对应若依顶层的 /login、/getRouters。
"""

from fastapi import APIRouter

from app.system.api.v1 import meta, auth, users, roles, menus, permissions, departments, posts, routes

# 系统管理模块组 — 统一挂 /system 前缀（对应若依的 /system/*）
system_router = APIRouter(prefix="/system")
system_router.include_router(users.router)
system_router.include_router(roles.router)
system_router.include_router(menus.router)
system_router.include_router(permissions.router)
system_router.include_router(departments.router)
system_router.include_router(posts.router)
system_router.include_router(meta.router)

# 总路由 — 版本前缀 /api/v1 由 main.py 设置
v1_router = APIRouter()
v1_router.include_router(system_router)   # /system/users、/system/roles ...
v1_router.include_router(auth.router)     # /auth/login、/auth/logout（登录/登出，顶层）
v1_router.include_router(routes.router)   # /routes（当前用户动态路由，顶层）

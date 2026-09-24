"""API v1 路由 — 当前唯一的 API 版本，整体挂载在 /api/v1 前缀下。

各模块路由 → URL 前缀（前缀在 router.py 汇总时设置）：

  auth.py        /auth          登录 / 登出
  users.py       /users         用户管理
  roles.py       /roles         角色管理
  menus.py       /menus         菜单管理
  permissions.py /permissions   权限管理
  departments.py /departments   部门管理
  posts.py       /posts         岗位管理
  meta.py        /meta          数据字典（错误码等）
  routes.py      /routes        当前用户动态路由（仅认证不鉴权）

汇总入口是 router.py，main.py 只 import 它一个文件。
完整 URL 映射见 router.py 顶部的注释。
"""

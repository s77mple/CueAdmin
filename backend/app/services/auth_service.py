"""
认证业务逻辑 — 登录的核心编排。

一次登录的完整数据流：

  #1 前端 POST /api/v1/auth/login { username, password }
  #2 AuthService.login() 开始执行：
     a. 从 DB 查用户（预加载角色+权限+菜单，一次查询搞定，避免 N+1）
     b. 用户不存在 → 也对假哈希跑一次 bcrypt（防止时间差枚举用户名）
     c. 用户存在 → verify_password() 比对 bcrypt 哈希
     d. 检查是否有角色（没角色 = 没法登录）
     e. 收集所有角色的权限 code → 去重排序
     f. 收集角色菜单 → admin 拥有全部菜单，普通用户只看角色绑定的菜单
     g. 补全缺失的父级菜单（子菜单的 parent 没分配给角色也能显示）
     h. 签发 JWT（payload = {sub, username, jti, exp}）
     i. 组装 LoginResponse（token + 用户信息 + 权限 + 角色 + 菜单）
  #3 返回 JSON:
     {
       code: 0,
       data: {
         access_token: "eyJ...",
         user: { id, username, display_name, ... },
         permissions: ["user:list", "user:create", ...],
         roles: [{ id: 1, code: "admin", name: "管理员" }],
         menus: [{ id: 1, code: "users", name: "用户管理", path: "/users", ... }]
       }
     }
  #4 前端收到后：
     - token 存 localStorage
     - 用户信息 + 角色 + 权限 存 pinia store
     - 菜单传给 initRouter() 生成动态路由
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User, Role
from app.schemas.auth import LoginResponse
from app.schemas.user import UserRead
from app.core.security import verify_password, create_access_token
from app.core.exceptions import BusinessException, ErrorCode
from app.services.menu_service import collect_user_menus


# 假哈希 — 用于用户不存在时消耗近似时间
# 这是一个已知明文的 bcrypt("a") 结果，用于防时序攻击
_DUMMY_HASH = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"


class AuthService:
    """#2 登录业务编排。

    不是在 API 层直接写逻辑，而是抽到 Service 层：
      - 方便单元测试（不需要启动 FastAPI 就能测登录逻辑）
      - 逻辑复用（以后可能有其他入口需要登录）
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def login(self, username: str, password: str, client: str | None = None) -> LoginResponse:

        # ---- #2a 一次查询预加载所有关联数据 ----
        # selectinload = 用第二条 SELECT IN (...) 查询关联数据
        # 登录只需要一次主查询 + 2 次 IN 查询（roles→permissions + roles→menus）
        stmt = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(Role.permissions),
                selectinload(User.roles).selectinload(Role.menus),
            )
            .where(User.username == username, User.is_active == True)
        )
        result = await self.session.execute(stmt)
        user = result.scalars().first()

        # ---- #2b 防用户名枚举 ----
        # 即使用户不存在，也跑一次 bcrypt（耗时约 100ms），
        # 让攻击者无法通过响应时间判断用户名是否存在
        if user is None:
            await verify_password(password, _DUMMY_HASH)
            raise BusinessException(ErrorCode.AUTH_INVALID_CREDENTIALS, "用户名或密码错误")

        # ---- #2c 验证密码 ----
        if not await verify_password(password, user.password_hash):
            raise BusinessException(ErrorCode.AUTH_INVALID_CREDENTIALS, "用户名或密码错误")

        # ---- #2d 检查是否有角色 ----
        if not user.roles:
            raise BusinessException(ErrorCode.AUTH_NO_ROLES, "该账号未分配角色，请联系管理员")

        # ---- #2e 收集权限 ----
        # 从所有角色收集权限 code，去重 + 排序
        # 例如：["menu:create", "menu:delete", "menu:list", "menu:update", ...]
        permissions = sorted({perm.code for role in user.roles for perm in role.permissions})

        # ---- #2f-g 收集菜单（统一收口到 menu_service）----
        menus = await collect_user_menus(self.session, user)

        # ---- #2h 签发 JWT ----
        token = create_access_token(user.id, user.username)

        # ---- #2i 组装响应 ----
        # 前端拿到这个响应后：
        #   1. access_token → 存 localStorage
        #   2. user → 存 pinia user store
        #   3. permissions → 存 pinia，用于 v-perms 指令判断按钮显隐
        #   4. roles → 存 pinia
        #   5. menus → 传给 initRouter() 生成动态路由
        return LoginResponse(
            access_token=token,
            user=UserRead.model_validate(user),
            permissions=permissions,
            roles=[{"id": r.id, "code": r.code, "name": r.name} for r in user.roles],
            menus=menus,
        )

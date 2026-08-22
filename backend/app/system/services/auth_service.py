"""认证业务逻辑 — 登录的核心编排。

用户不存在时也对假哈希跑一次 bcrypt，防止通过响应时间差枚举用户名。
登录响应不含 menus —— 菜单统一收口到 collect_user_menus()，由 /routes 下发，
避免同一份菜单塞两遍。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.system.models import User, Role
from app.system.schemas.auth import LoginResponse
from app.system.schemas.user import UserRead
from app.core.security import verify_password, create_access_token
from app.core.exceptions import BusinessException, ErrorCode


# 假哈希 — 用于用户不存在时消耗近似时间
# 这是一个已知明文的 bcrypt("a") 结果，用于防时序攻击
_DUMMY_HASH = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"


class AuthService:
    """登录业务编排。抽到 Service 层是为了方便单元测试和逻辑复用。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def login(self, username: str, password: str, client: str | None = None) -> LoginResponse:

        # ---- 一次查询预加载所有关联数据 ----
        # selectinload = 用第二条 SELECT IN (...) 查询关联数据
        # 登录只需一次主查询 + 1 次 IN 查询（roles→permissions）
        # 菜单不在这里加载：登录响应不含 menus，动态路由统一走 /routes
        stmt = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(Role.permissions),
            )
            .where(User.username == username, User.is_active == True)
        )
        result = await self.session.execute(stmt)
        user = result.scalars().first()

        # ---- 防用户名枚举 ----
        # 即使用户不存在，也跑一次 bcrypt（耗时约 100ms），
        # 让攻击者无法通过响应时间判断用户名是否存在
        if user is None:
            await verify_password(password, _DUMMY_HASH)
            raise BusinessException(ErrorCode.AUTH_INVALID_CREDENTIALS, "用户名或密码错误")

        # ---- 验证密码 ----
        if not await verify_password(password, user.password_hash):
            raise BusinessException(ErrorCode.AUTH_INVALID_CREDENTIALS, "用户名或密码错误")

        # ---- 检查是否有角色 ----
        if not user.roles:
            raise BusinessException(ErrorCode.AUTH_NO_ROLES, "该账号未分配角色，请联系管理员")

        # ---- 收集权限 ----
        # 从所有角色收集权限 code，去重 + 排序
        # 例如：["menu:create", "menu:delete", "menu:list", "menu:update", ...]
        permissions = sorted({perm.code for role in user.roles for perm in role.permissions})

        # ---- 签发 JWT ----
        token = create_access_token(user.id, user.username)

        # ---- 组装响应 ----
        return LoginResponse(
            access_token=token,
            user=UserRead.model_validate(user),
            permissions=permissions,
            roles=[{"id": r.id, "code": r.code, "name": r.name} for r in user.roles],
        )

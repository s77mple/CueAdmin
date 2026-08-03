"""认证业务逻辑。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User, Role, Menu
from app.schemas.auth import LoginResponse
from app.schemas.user import UserRead
from app.core.security import verify_password, create_access_token
from app.core.exceptions import BusinessException, ErrorCode


# 防止用户名枚举：用户不存在时也用 bcrypt 消耗近似时间
_DUMMY_HASH = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def login(self, username: str, password: str, client: str | None = None) -> LoginResponse:
        # 1. 用户名在创建时已校验不允许空格，此处无需 strip

        # 2. 从数据库加载用户，同时预加载角色、权限、菜单（一次查询，避免后续 N+1）
        stmt = (
            select(User)
            .options(
                selectinload(User.roles).selectinload(Role.permissions),
                selectinload(User.roles).selectinload(Role.menus),
            )
            .where(User.username == username, User.is_active == True)
        )
        result = await self.db.execute(stmt)
        user = result.scalars().first()

        # 3. 用户不存在：也跑一次 bcrypt，防止通过响应时间差异枚举用户名
        if user is None:
            await verify_password(password, _DUMMY_HASH)
            raise BusinessException(ErrorCode.AUTH_INVALID_CREDENTIALS, "用户名或密码错误")

        # 4. 验证密码（bcrypt 比对）
        if not await verify_password(password, user.password_hash):
            raise BusinessException(ErrorCode.AUTH_INVALID_CREDENTIALS, "用户名或密码错误")

        # 5. 检查是否分配了角色（没角色无法登录，因为权限和菜单都来自角色）
        if not user.roles:
            raise BusinessException(ErrorCode.AUTH_NO_ROLES, "该账号未分配角色，请联系管理员")

        # 6. 从所有角色中收集权限 code，去重排序
        permissions = sorted({perm.code for role in user.roles for perm in role.permissions})

        # 7. 收集菜单：系统角色拥有全部菜单，否则仅角色绑定的菜单
        seen: set[str] = set()
        menus: list[dict] = []
        if any(role.is_system for role in user.roles):
            stmt = select(Menu).order_by(Menu.sort_order, Menu.id)
            result = await self.db.execute(stmt)
            all_menus = result.scalars().all()
            for m in all_menus:
                menus.append({
                    "code": m.code, "name": m.name, "icon": m.icon, "path": m.path,
                    "component": m.component,
                    "parent_id": m.parent_id, "sort_order": m.sort_order,
                })
        else:
            for role in user.roles:
                for m in role.menus:
                    if m.code not in seen:
                        seen.add(m.code)
                        menus.append({
                            "code": m.code, "name": m.name, "icon": m.icon, "path": m.path,
                            "component": m.component,
                            "parent_id": m.parent_id, "sort_order": m.sort_order,
                        })

        menus.sort(key=lambda m: m["sort_order"])

        # 8. 签发 JWT（payload 包含 user_id、username、唯一 jti、签发时间、过期时间）
        token = create_access_token(user.id, user.username)

        # 9. 组装登录响应：token + 用户信息 + 权限列表 + 角色列表 + 菜单列表
        return LoginResponse(
            access_token=token,
            user=UserRead.model_validate(user),
            permissions=permissions,
            roles=[{"id": r.id, "code": r.code, "name": r.name} for r in user.roles],
            menus=menus,
        )

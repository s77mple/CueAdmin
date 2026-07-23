"""认证业务逻辑。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import User, Role
from app.schemas.auth import LoginResponse
from app.schemas.user import UserRead
from app.core.security import verify_password, create_access_token
from app.core.exceptions import ValidationException


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def login(self, username: str, password: str, client: str | None = None) -> LoginResponse:
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

        if not user or not await verify_password(password, user.password_hash):
            raise ValidationException("用户名或密码错误")

        if not user.roles:
            raise ValidationException("该账号未分配角色，请联系管理员")

        permissions = sorted({perm.code for role in user.roles for perm in role.permissions})

        seen: set[str] = set()
        menus: list[dict] = []
        for role in user.roles:
            for m in role.menus:
                if m.code not in seen:
                    seen.add(m.code)
                    menus.append({
                        "code": m.code, "name": m.name, "icon": m.icon, "path": m.path,
                        "parent_id": m.parent_id, "sort_order": m.sort_order,
                    })

        token = create_access_token(user.id, user.username)
        return LoginResponse(
            access_token=token,
            user=UserRead.model_validate(user),
            permissions=permissions,
            menus=menus,
        )

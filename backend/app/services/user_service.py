"""
用户业务逻辑 — 用户的 CRUD + 校验 + 权限缓存管理。

从 api/users.py 提取而来，API 层只做参数提取和响应包装。
"""

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models import User, Role, Department
from app.core.security import hash_password
from app.core.paginate import paginate
from app.core.exceptions import BusinessException, ErrorCode
from app.schemas.response import PageData
from app.schemas.user import UserCreate, UserUpdate, UserPatch, UserRead


class UserService:
    """用户管理业务逻辑。

    用法：
        svc = UserService(session)
        result = await svc.list_users(role_id=1, is_active=True, page=1, page_size=20)
        user = await svc.create_user(body)
    """

    def __init__(self, session: AsyncSession, redis_client: aioredis.Redis | None = None):
        self.session = session
        self.redis = redis_client

    # ============================================================
    # 查询
    # ============================================================

    async def list_users(
        self,
        role_id: int | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PageData[UserRead]:
        """分页用户列表，支持按角色和启用状态筛选。"""
        stmt = select(User).options(selectinload(User.roles), joinedload(User.department))

        if role_id is not None:
            stmt = stmt.join(User.roles).where(Role.id == role_id)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)

        stmt = stmt.order_by(User.id.asc())
        return await paginate(self.session, stmt, page, page_size)

    async def get_user_for_update(self, user_id: int) -> User:
        """带行级锁获取用户（用于更新/删除操作）。"""
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.roles), joinedload(User.department))
            .where(User.id == user_id)
            .with_for_update()
        )
        target = result.scalars().first()
        if not target:
            raise BusinessException(ErrorCode.USER_NOT_FOUND, f"用户不存在: {user_id}")
        return target

    # ============================================================
    # 创建
    # ============================================================

    async def create_user(self, body: UserCreate) -> User:
        """创建用户 — 双重唯一性校验 + 外键验证。"""
        # 应用层唯一性检查
        if (await self.session.execute(select(User).where(User.username == body.username))).scalars().first():
            raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")

        # 验证部门存在
        await self._validate_department(body.department_id)

        new_user = User(
            username=body.username,
            password_hash=await hash_password(body.password),
            display_name=body.display_name,
            phone=body.phone,
            department_id=body.department_id,
        )

        # 验证角色存在 + 赋值
        if body.role_ids:
            roles = (await self.session.execute(
                select(Role).where(Role.id.in_(body.role_ids))
            )).scalars().all()
            if len(roles) != len(body.role_ids):
                found = {r.id for r in roles}
                invalid = [rid for rid in body.role_ids if rid not in found]
                raise BusinessException(ErrorCode.VALIDATION_ERROR, f"角色 ID 不存在: {invalid}")
            new_user.roles = roles

        self.session.add(new_user)

        # 数据库层唯一性兜底（TOCTOU 防护）
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")

        # commit 后重新查询并 eager load roles + department：
        # 否则响应序列化时访问 new_user.roles 会触发 async lazy-load（MissingGreenlet 崩溃）
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.roles), joinedload(User.department))
            .where(User.id == new_user.id)
        )
        return result.scalars().first()

    # ============================================================
    # 全量更新
    # ============================================================

    async def update_user(self, user_id: int, body: UserUpdate) -> User:
        """PUT 全量更新 — 所有字段覆盖写入。"""
        target = await self.get_user_for_update(user_id)
        self._guard_superadmin(target)

        # 用户名
        if body.username != target.username:
            await self._validate_username_unique(body.username, exclude_user_id=user_id)
            target.username = body.username

        target.display_name = body.display_name
        target.phone = body.phone

        # 禁用保护
        if not body.is_active:
            self._guard_superadmin(target)
            await self._guard_last_admin()

        target.is_active = body.is_active

        # 部门
        await self._validate_department(body.department_id)
        target.department_id = body.department_id

        # 角色
        old_role_ids = {r.id for r in target.roles}
        await self._resolve_roles(target, body.role_ids)
        roles_changed = {r.id for r in target.roles} != old_role_ids

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")
        await self.session.refresh(target)

        if roles_changed:
            await self._clear_perm_cache(user_id)

        return target

    # ============================================================
    # 部分更新
    # ============================================================

    async def patch_user(self, user_id: int, body: UserPatch) -> User:
        """PATCH 部分更新 — 只改传了的字段。"""
        target = await self.get_user_for_update(user_id)
        self._guard_superadmin(target)
        data = body.model_dump(exclude_unset=True)

        if "username" in data:
            if data["username"] is None:
                raise BusinessException(ErrorCode.VALIDATION_ERROR, "username 不能为 null")
            if data["username"] != target.username:
                await self._validate_username_unique(data["username"], exclude_user_id=user_id)
                target.username = data["username"]

        if "display_name" in data:
            if data["display_name"] is None:
                raise BusinessException(ErrorCode.VALIDATION_ERROR, "display_name 不能为 null")
            target.display_name = data["display_name"]

        if "phone" in data:
            target.phone = data["phone"]

        if "is_active" in data:
            if not data["is_active"]:
                self._guard_superadmin(target)
                await self._guard_last_admin()
            target.is_active = data["is_active"]

        if "department_id" in data:
            await self._validate_department(data["department_id"])
            target.department_id = data["department_id"]

        if "role_ids" in data:
            await self._resolve_roles(target, data["role_ids"])

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")
        await self.session.refresh(target)

        if "role_ids" in data:
            await self._clear_perm_cache(user_id)

        return target

    # ============================================================
    # 删除
    # ============================================================

    async def delete_user(self, user_id: int, operator_id: int, hard: bool = False) -> str:
        """软禁用（默认）或硬删除（?hard=true，仅已禁用用户）。"""
        result = await self.session.execute(
            select(User).options(selectinload(User.roles)).where(User.id == user_id).with_for_update()
        )
        target = result.scalars().first()
        if not target:
            raise BusinessException(ErrorCode.USER_NOT_FOUND, f"用户不存在: {user_id}")

        if operator_id == user_id:
            raise BusinessException(ErrorCode.CONFLICT, "不允许操作自己的账号")
        self._guard_superadmin(target)

        if hard:
            if target.is_active:
                raise BusinessException(ErrorCode.CONFLICT, "不允许彻底删除启用状态的用户，请先禁用")
            if any(r.code == "admin" for r in target.roles):
                admin_count = (await self.session.execute(
                    select(User).join(User.roles).where(
                        Role.code == "admin", User.is_active == True
                    ).with_for_update()
                )).scalars().all()
                if len(admin_count) < 1:
                    raise BusinessException(ErrorCode.CONFLICT, "不允许删除最后一个拥有管理员角色的用户")

            await self._clear_perm_cache(user_id)
            await self.session.delete(target)
            try:
                await self.session.commit()
            except IntegrityError:
                await self.session.rollback()
                raise BusinessException(ErrorCode.CONFLICT, "删除失败：存在关联数据")
            return "已彻底删除"
        else:
            if not target.is_active:
                raise BusinessException(ErrorCode.CONFLICT, "该用户已被禁用")
            if any(r.code == "admin" for r in target.roles):
                await self._guard_last_admin()

            target.is_active = False
            await self.session.commit()
            return "已禁用"

    # ============================================================
    # 私有辅助方法
    # ============================================================

    async def _validate_username_unique(self, username: str, exclude_user_id: int | None = None) -> None:
        """检查用户名唯一（编辑时排除自己）。"""
        stmt = select(User).where(User.username == username)
        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)
        if (await self.session.execute(stmt)).scalars().first():
            raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")

    async def _validate_department(self, department_id: int | None) -> None:
        """校验部门存在。"""
        if department_id is not None:
            dept = (await self.session.execute(select(Department).where(Department.id == department_id))).scalars().first()
            if not dept:
                raise BusinessException(ErrorCode.VALIDATION_ERROR, f"部门不存在: {department_id}")

    async def _resolve_roles(self, target: User, role_ids: list[int] | None) -> None:
        """验证角色 ID 存在并赋值，包含最后管理员保护。"""
        role_ids = role_ids or []  # None（未传）与空列表均视为清空角色
        roles = (await self.session.execute(
            select(Role).where(Role.id.in_(role_ids))
        )).scalars().all()
        if len(roles) != len(role_ids):
            found = {r.id for r in roles}
            invalid = [rid for rid in role_ids if rid not in found]
            raise BusinessException(ErrorCode.VALIDATION_ERROR, f"角色 ID 不存在: {invalid}")

        admin_role = next((r for r in roles if r.code == "admin"), None)
        had_admin = any(r.code == "admin" for r in target.roles)
        will_lose_admin = had_admin and admin_role is None

        if will_lose_admin:
            admin_count = (await self.session.execute(
                select(User).join(User.roles).where(
                    Role.code == "admin", User.is_active == True
                ).with_for_update()
            )).scalars().all()
            if len(admin_count) <= 1:
                raise BusinessException(ErrorCode.CONFLICT, "不允许移除最后一个管理员的 admin 角色")

        target.roles = roles

    async def _guard_last_admin(self) -> None:
        """确保不禁用/删除最后一个管理员。"""
        admin_count = (await self.session.execute(
            select(User).join(User.roles).where(
                Role.code == "admin", User.is_active == True
            ).with_for_update()
        )).scalars().all()
        if len(admin_count) <= 1:
            raise BusinessException(ErrorCode.CONFLICT, "不允许禁用最后一个管理员")

    @staticmethod
    def _guard_superadmin(target: User) -> None:
        """禁止操作超级管理员（admin 用户名）。"""
        if target.username == "admin":
            raise BusinessException(ErrorCode.USER_CANNOT_DISABLE_SUPERADMIN, "不允许操作超级管理员")

    async def _clear_perm_cache(self, user_id: int) -> None:
        """清除用户权限缓存。"""
        if not self.redis:
            return
        try:
            await self.redis.delete(f"perm:{user_id}")
        except aioredis.RedisError:
            pass  # Redis 故障不影响业务

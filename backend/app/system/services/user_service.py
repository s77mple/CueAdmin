"""
用户业务逻辑 — 用户的 CRUD + 校验 + 权限缓存管理。

数据访问收口到 Repository（见 app/system/repositories/user.py 等），
本层只做业务校验 + 事务提交 + 缓存清除。
"""

from redis.asyncio import Redis, RedisError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.system.models import User
from app.core.security import hash_password
from app.core.exceptions import BusinessException, ErrorCode
from app.core.response import PageData
from app.utils.tree import collect_subtree_ids
from app.system.repositories import UserRepository, RoleRepository, DepartmentRepository, PostRepository
from app.system.schemas.user import (
    UserCreate, UserUpdate, UserPatch, UserListItem, UserDetail,
)


class UserService:
    """用户管理业务逻辑。

    用法：
        svc = UserService(session)
        result = await svc.list_users(role_id=1, is_active=True, page=1, page_size=20)
        user = await svc.create_user(body)
    """

    def __init__(self, session: AsyncSession, redis_client: Redis | None = None):
        self.session = session
        self.redis = redis_client
        self.users = UserRepository(session)
        self.roles = RoleRepository(session)
        self.departments = DepartmentRepository(session)
        self.posts = PostRepository(session)

    # 查询

    async def list_users(
        self,
        role_id: int | None = None,
        is_active: bool | None = None,
        dept_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PageData[UserListItem]:
        """分页用户列表，支持按角色、启用状态、部门（含全部子孙）筛选。"""
        dept_ids = None
        if dept_id is not None:
            # 学 RuoYi：deptId 匹配「该部门 + 全部子孙部门」（若依靠 ancestors + find_in_set）。
            # 部门量小，全量拉平后用 collect_subtree_ids 收子树 id 集合，不必加 ancestors 列
            departments = await self.departments.list_departments()
            dept_ids = collect_subtree_ids(
                departments,
                root_id=dept_id,
                get_id=lambda d: d.id,
                get_parent_id=lambda d: d.parent_id,
            )
        return await self.users.list_users(
            role_id=role_id, is_active=is_active, dept_ids=dept_ids, page=page, page_size=page_size,
        )

    async def get_user_for_update(self, user_id: int) -> User:
        """带行级锁获取用户（用于更新/删除操作）。"""
        target = await self.users.get_for_update_with_roles_posts(user_id)
        if not target:
            raise BusinessException(ErrorCode.USER_NOT_FOUND, f"用户不存在: {user_id}")
        return target

    async def get_user_detail(self, user_id: int) -> UserDetail:
        """单个用户详情（编辑回显）— user 纯列 + 全量角色/岗位下拉 + 已分配 role_ids/post_ids。

        学 RuoYi getInfo：roles/posts = 全部可选（下拉选项），role_ids/post_ids = 已分配（勾选回显）。
        部门树由列表页 /departments/tree 提供，不进详情。
        role_ids/post_ids 装配只此一处：其余接口返回纯列 UserRead，无需预载 roles/posts。
        """
        user = await self.users.get_with_roles_posts(user_id)
        if not user:
            raise BusinessException(ErrorCode.USER_NOT_FOUND, f"用户不存在: {user_id}")
        roles = await self.roles.list_roles(page=1, page_size=100)
        posts = await self.posts.list_all()  # 全部岗位（下拉选项）
        return UserDetail(
            user=user,
            roles=roles.items,
            role_ids=[role.id for role in user.roles],  # 该用户已分配（编辑回显勾选）
            posts=posts,
            post_ids=[post.id for post in user.posts],  # 该用户已分配岗位（编辑回显勾选）
        )

    # 创建

    async def create_user(self, body: UserCreate) -> User:
        """创建用户 — 双重唯一性校验 + 外键验证。"""
        # 应用层唯一性检查
        if await self.users.get_by_username(body.username):
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
            roles = await self.roles.get_by_ids(body.role_ids)
            if len(roles) != len(body.role_ids):
                found = {r.id for r in roles}
                invalid = [rid for rid in body.role_ids if rid not in found]
                raise BusinessException(ErrorCode.VALIDATION_ERROR, f"角色 ID 不存在: {invalid}")
            new_user.roles = roles

        # 验证岗位存在 + 赋值
        await self._resolve_posts(new_user, body.post_ids)

        self.users.add(new_user)

        # 数据库层唯一性兜底（TOCTOU 防护）
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")

        # commit 后重查拿回 server 生成的时间戳；UserRead 纯列，无需预载 roles
        return await self.users.get(new_user.id)

    # 全量更新

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

        # 禁用保护（superadmin 已在上方校验过，这里只需确保不删最后一个管理员）
        if not body.is_active:
            await self._guard_last_admin()

        target.is_active = body.is_active

        # 部门
        await self._validate_department(body.department_id)
        target.department_id = body.department_id

        # 角色
        old_role_ids = {r.id for r in target.roles}
        await self._resolve_roles(target, body.role_ids)
        roles_changed = {r.id for r in target.roles} != old_role_ids

        # 岗位（只影响关联表，不涉及权限 → 不触发缓存清除）
        await self._resolve_posts(target, body.post_ids)

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")
        await self.session.refresh(target)

        if roles_changed:
            await self._clear_perm_cache(user_id)

        return target

    # 部分更新

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
                await self._guard_last_admin()
            target.is_active = data["is_active"]

        if "department_id" in data:
            await self._validate_department(data["department_id"])
            target.department_id = data["department_id"]

        if "role_ids" in data:
            await self._resolve_roles(target, data["role_ids"])

        if "post_ids" in data:
            await self._resolve_posts(target, data["post_ids"])

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")
        await self.session.refresh(target)

        if "role_ids" in data:
            await self._clear_perm_cache(user_id)

        return target

    # 删除

    async def delete_user(self, user_id: int, operator_id: int, hard: bool = False) -> str:
        """软禁用（默认）或硬删除（?hard=true，仅已禁用用户）。"""
        target = await self.users.get_for_update_with_roles_posts(user_id)
        if not target:
            raise BusinessException(ErrorCode.USER_NOT_FOUND, f"用户不存在: {user_id}")

        if operator_id == user_id:
            raise BusinessException(ErrorCode.CONFLICT, "不允许操作自己的账号")
        self._guard_superadmin(target)

        if hard:
            if target.is_active:
                raise BusinessException(ErrorCode.CONFLICT, "不允许彻底删除启用状态的用户，请先禁用")
            if any(r.code == "admin" for r in target.roles):
                if await self.users.count_active_admins() < 1:
                    raise BusinessException(ErrorCode.CONFLICT, "不允许删除最后一个拥有管理员角色的用户")

            await self._clear_perm_cache(user_id)
            await self.users.delete(target)
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

    # 私有辅助方法

    async def _validate_username_unique(self, username: str, exclude_user_id: int | None = None) -> None:
        """检查用户名唯一（编辑时排除自己）。"""
        if await self.users.get_by_username(username, exclude_user_id):
            raise BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS, "用户名已存在")

    async def _validate_department(self, department_id: int | None) -> None:
        """校验部门存在。"""
        if department_id is not None:
            if not await self.departments.get(department_id):
                raise BusinessException(ErrorCode.VALIDATION_ERROR, f"部门不存在: {department_id}")

    async def _resolve_roles(self, target: User, role_ids: list[int] | None) -> None:
        """验证角色 ID 存在并赋值，包含最后管理员保护。"""
        role_ids = role_ids or []  # None（未传）与空列表均视为清空角色
        roles = await self.roles.get_by_ids(role_ids)
        if len(roles) != len(role_ids):
            found = {r.id for r in roles}
            invalid = [rid for rid in role_ids if rid not in found]
            raise BusinessException(ErrorCode.VALIDATION_ERROR, f"角色 ID 不存在: {invalid}")

        admin_role = next((r for r in roles if r.code == "admin"), None)
        had_admin = any(r.code == "admin" for r in target.roles)
        will_lose_admin = had_admin and admin_role is None

        if will_lose_admin:
            if await self.users.count_active_admins() <= 1:
                raise BusinessException(ErrorCode.CONFLICT, "不允许移除最后一个管理员的 admin 角色")

        target.roles = roles

    async def _resolve_posts(self, target: User, post_ids: list[int] | None) -> None:
        """验证岗位 ID 存在并赋值（与 _resolve_roles 同构）。

        岗位不参与权限判断，改岗位无需清 perm 缓存；None 与空列表都视为清空岗位。
        """
        post_ids = post_ids or []
        posts = await self.posts.get_by_ids(post_ids)
        if len(posts) != len(post_ids):
            found = {p.id for p in posts}
            invalid = [pid for pid in post_ids if pid not in found]
            raise BusinessException(ErrorCode.VALIDATION_ERROR, f"岗位 ID 不存在: {invalid}")

        target.posts = posts

    async def _guard_last_admin(self) -> None:
        """确保不禁用/删除最后一个管理员。"""
        if await self.users.count_active_admins() <= 1:
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
        except RedisError:
            pass  # Redis 故障不影响业务

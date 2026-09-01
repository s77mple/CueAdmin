"""
角色业务逻辑 — 角色的 CRUD + 权限/菜单关联 + 缓存主动失效。

数据访问收口到 Repository，本层只做业务校验 + 事务提交 + 缓存清除。
"""

from redis.asyncio import Redis, RedisError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.system.models import Role
from app.core.exceptions import BusinessException, ErrorCode
from app.core.logger import logger
from app.core.response import PageData
from app.system.repositories import RoleRepository, PermissionRepository, MenuRepository
from app.system.schemas.role import RoleCreate, RoleUpdate, RoleItem


class RoleService:
    """角色管理业务逻辑。

    用法：
        svc = RoleService(session, redis_client)
        roles = await svc.list_roles()
        role = await svc.create_role(body)
    """

    def __init__(self, session: AsyncSession, redis_client: Redis | None = None):
        self.session = session
        self.redis = redis_client
        self.roles = RoleRepository(session)
        self.permissions = PermissionRepository(session)
        self.menus = MenuRepository(session)

    # 查询

    async def list_roles(self, page: int = 1, page_size: int = 100) -> PageData[RoleItem]:
        """分页返回角色（预加载权限和菜单）。角色数量少，默认 page_size=100 一次返回全部。"""
        return await self.roles.list_roles(page, page_size)

    async def get_role_for_update(self, role_id: int) -> Role:
        """带行级锁获取角色。"""
        role = await self.roles.get_for_update_with_relations(role_id)
        if not role:
            raise BusinessException(ErrorCode.ROLE_NOT_FOUND, f"角色不存在: {role_id}")
        return role

    # 创建

    async def create_role(self, body: RoleCreate) -> Role:
        """创建角色 — 双重唯一性保护。"""
        if await self.roles.get_by_code(body.code):
            raise BusinessException(ErrorCode.ROLE_CODE_EXISTS, "角色编码已存在")

        role = Role(code=body.code, name=body.name, description=body.description)

        await self._resolve_relations(role, body.permission_codes, body.menu_ids)

        self.roles.add(role)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise BusinessException(ErrorCode.ROLE_CODE_EXISTS, "角色编码已存在")
        await self.session.refresh(role)
        return role

    # 全量更新

    async def update_role(self, role_id: int, body: RoleUpdate) -> Role:
        """PUT 全量更新 — 系统角色不可修改。"""
        role = await self.get_role_for_update(role_id)
        self._guard_system(role)

        role.name = body.name
        role.description = body.description
        await self._resolve_relations(role, body.permission_codes, body.menu_ids)
        await self.session.commit()

        await self._clear_role_users_cache(role_id, role.code)
        return role

    # 删除

    async def delete_role(self, role_id: int) -> str:
        """删除角色 — 系统角色不可删除，关联用户缓存同步清除。"""
        role = await self.roles.get_for_update(role_id)
        if not role:
            raise BusinessException(ErrorCode.ROLE_NOT_FOUND, f"角色不存在: {role_id}")
        self._guard_system(role)

        # 删前查出关联用户（用于缓存清除）
        try:
            rows = await self.roles.get_user_ids(role_id)
        except SQLAlchemyError:
            rows = []
            logger.warning("查询角色关联用户失败，跳过缓存清除")

        await self.roles.delete(role)
        await self.session.commit()

        # 清除所有关联用户的权限缓存
        for uid in rows:
            await self._safe_delete_cache(f"perm:{uid}")
        if rows:
            logger.info("角色 [{}] 已删除，清除 {} 个用户缓存", role.code, len(rows))
        return "删除成功"

    # 私有辅助方法

    async def _resolve_relations(
        self,
        role: Role,
        permission_codes: list[str] | None = None,
        menu_ids: list[int] | None = None,
    ) -> None:
        """校验权限/菜单关联并赋给角色。None 表示不修改该关联。"""
        if permission_codes is not None:
            perms = await self.permissions.get_by_codes(permission_codes)
            if len(perms) != len(permission_codes):
                found = {p.code for p in perms}
                invalid = [c for c in permission_codes if c not in found]
                raise BusinessException(ErrorCode.VALIDATION_ERROR, f"权限 code 不存在: {invalid}")
            role.permissions = perms

        if menu_ids is not None:
            menus = await self.menus.get_by_ids(menu_ids)
            if len(menus) != len(menu_ids):
                found = {m.id for m in menus}
                invalid = [mid for mid in menu_ids if mid not in found]
                raise BusinessException(ErrorCode.VALIDATION_ERROR, f"菜单 ID 不存在: {invalid}")
            role.menus = menus

    async def _clear_role_users_cache(self, role_id: int, role_code: str) -> None:
        """角色权限/菜单变更后，清除所有关联用户的 Redis 权限缓存。"""
        try:
            rows = await self.roles.get_user_ids(role_id)
        except SQLAlchemyError:
            logger.warning("查询角色关联用户失败，跳过缓存清除")
            return

        for uid in rows:
            await self._safe_delete_cache(f"perm:{uid}")

        logger.info("角色 [{}] 权限/菜单变更，已清除 {} 个用户缓存", role_code, len(rows))

    async def _safe_delete_cache(self, key: str) -> None:
        """安全删除 Redis 缓存 — 失败不抛异常。"""
        if not self.redis:
            return
        try:
            await self.redis.delete(key)
        except RedisError:
            pass

    @staticmethod
    def _guard_system(role: Role) -> None:
        """系统角色不允许修改/删除。"""
        if role.is_system:
            raise BusinessException(ErrorCode.ROLE_IS_SYSTEM, "不允许修改系统角色")

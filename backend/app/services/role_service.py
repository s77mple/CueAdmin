"""
角色业务逻辑 — 角色的 CRUD + 权限/菜单关联 + 缓存主动失效。

从 api/roles.py 提取而来，API 层只做参数提取和响应包装。
"""

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Role, Permission, Menu
from app.models.associations import user_roles
from app.core.exceptions import BusinessException, ErrorCode
from app.core.paginate import paginate
from app.core.logger import logger
from app.schemas.response import PageData


class RoleService:
    """角色管理业务逻辑。

    用法：
        svc = RoleService(db, redis_client)
        roles = await svc.list_roles()
        role = await svc.create_role(body)
    """

    def __init__(self, db: AsyncSession, redis_client: aioredis.Redis | None = None):
        self.db = db
        self.redis = redis_client

    # ============================================================
    # 查询
    # ============================================================

    async def list_roles(self, page: int = 1, page_size: int = 100) -> PageData:
        """分页返回角色（预加载权限和菜单）。角色数量少，默认 page_size=100 一次返回全部。"""
        stmt = (
            select(Role)
            .options(selectinload(Role.permissions), selectinload(Role.menus))
            .order_by(Role.id.asc())
        )
        return await paginate(self.db, stmt, page, page_size)

    async def get_role_for_update(self, role_id: int) -> Role:
        """带行级锁获取角色。"""
        result = await self.db.execute(
            select(Role)
            .options(selectinload(Role.permissions), selectinload(Role.menus))
            .where(Role.id == role_id)
            .with_for_update()
        )
        role = result.scalars().first()
        if not role:
            raise BusinessException(ErrorCode.ROLE_NOT_FOUND, f"角色不存在: {role_id}")
        return role

    # ============================================================
    # 创建
    # ============================================================

    async def create_role(self, body) -> Role:
        """创建角色 — 双重唯一性保护。"""
        if (await self.db.execute(select(Role).where(Role.code == body.code))).scalars().first():
            raise BusinessException(ErrorCode.ROLE_CODE_EXISTS, "角色编码已存在")

        role = Role(code=body.code, name=body.name, description=body.description)

        await self._resolve_relations(role, body.permission_codes, body.menu_ids)

        self.db.add(role)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise BusinessException(ErrorCode.ROLE_CODE_EXISTS, "角色编码已存在")
        await self.db.refresh(role)
        return role

    # ============================================================
    # 全量更新
    # ============================================================

    async def update_role(self, role_id: int, body) -> Role:
        """PUT 全量更新 — 系统角色不可修改。"""
        role = await self.get_role_for_update(role_id)
        self._guard_system(role)

        role.name = body.name
        role.description = body.description
        await self._resolve_relations(role, body.permission_codes, body.menu_ids)
        await self.db.commit()

        await self._clear_role_users_cache(role_id, role.code)
        return role

    # ============================================================
    # 部分更新
    # ============================================================

    async def patch_role(self, role_id: int, body) -> Role:
        """PATCH 部分更新 — 只改传了的字段。"""
        role = await self.get_role_for_update(role_id)
        self._guard_system(role)

        data = body.model_dump(exclude_unset=True)
        relations_changed = False

        if "name" in data:
            if data["name"] is None:
                raise BusinessException(ErrorCode.VALIDATION_ERROR, "name 不能为 null")
            role.name = data["name"]
        if "description" in data:
            role.description = data["description"]
        if "permission_codes" in data:
            await self._resolve_relations(role, permission_codes=data["permission_codes"])
            relations_changed = True
        if "menu_ids" in data:
            await self._resolve_relations(role, menu_ids=data["menu_ids"])
            relations_changed = True

        await self.db.commit()

        if relations_changed:
            await self._clear_role_users_cache(role_id, role.code)
        return role

    # ============================================================
    # 删除
    # ============================================================

    async def delete_role(self, role_id: int) -> str:
        """删除角色 — 系统角色不可删除，关联用户缓存同步清除。"""
        result = await self.db.execute(
            select(Role).where(Role.id == role_id).with_for_update()
        )
        role = result.scalars().first()
        if not role:
            raise BusinessException(ErrorCode.ROLE_NOT_FOUND, f"角色不存在: {role_id}")
        self._guard_system(role)

        # 删前查出关联用户（用于缓存清除）
        try:
            rows = (await self.db.execute(
                select(user_roles.c.user_id).where(user_roles.c.role_id == role_id)
            )).all()
        except SQLAlchemyError:
            rows = []
            logger.warning("查询角色关联用户失败，跳过缓存清除")

        await self.db.delete(role)
        await self.db.commit()

        # 清除所有关联用户的权限缓存
        for (uid,) in rows:
            await self._safe_delete_cache(f"perm:{uid}")
        if rows:
            logger.info("角色 [{}] 已删除，清除 {} 个用户缓存", role.code, len(rows))
        return "删除成功"

    # ============================================================
    # 私有辅助方法
    # ============================================================

    async def _resolve_relations(
        self,
        role: Role,
        permission_codes: list[str] | None = None,
        menu_ids: list[int] | None = None,
    ):
        """校验权限/菜单关联并赋给角色。None 表示不修改该关联。"""
        if permission_codes is not None:
            perms = (await self.db.execute(
                select(Permission).where(Permission.code.in_(permission_codes))
            )).scalars().all()
            if len(perms) != len(permission_codes):
                found = {p.code for p in perms}
                invalid = [c for c in permission_codes if c not in found]
                raise BusinessException(ErrorCode.VALIDATION_ERROR, f"权限 code 不存在: {invalid}")
            role.permissions = perms

        if menu_ids is not None:
            menus = (await self.db.execute(
                select(Menu).where(Menu.id.in_(menu_ids))
            )).scalars().all()
            if len(menus) != len(menu_ids):
                found = {m.id for m in menus}
                invalid = [mid for mid in menu_ids if mid not in found]
                raise BusinessException(ErrorCode.VALIDATION_ERROR, f"菜单 ID 不存在: {invalid}")
            role.menus = menus

    async def _clear_role_users_cache(self, role_id: int, role_code: str):
        """角色权限/菜单变更后，清除所有关联用户的 Redis 权限缓存。"""
        try:
            rows = (await self.db.execute(
                select(user_roles.c.user_id).where(user_roles.c.role_id == role_id)
            )).all()
        except SQLAlchemyError:
            logger.warning("查询角色关联用户失败，跳过缓存清除")
            return

        for (uid,) in rows:
            await self._safe_delete_cache(f"perm:{uid}")

        logger.info("角色 [{}] 权限/菜单变更，已清除 {} 个用户缓存", role_code, len(rows))

    async def _safe_delete_cache(self, key: str):
        """安全删除 Redis 缓存 — 失败不抛异常。"""
        if not self.redis:
            return
        try:
            await self.redis.delete(key)
        except aioredis.RedisError:
            pass

    @staticmethod
    def _guard_system(role: Role):
        """系统角色不允许修改/删除。"""
        if role.is_system:
            raise BusinessException(ErrorCode.ROLE_IS_SYSTEM, "不允许修改系统角色")

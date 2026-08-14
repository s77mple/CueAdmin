"""
部门业务逻辑 — 部门的树形 CRUD + 循环检测。

从 api/departments.py 提取而来。
"""

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Department, User
from app.core.exceptions import BusinessException, ErrorCode


class DepartmentService:
    """部门管理业务逻辑。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================================
    # 查询
    # ============================================================

    async def list_departments(self) -> list[Department]:
        """返回全部部门（扁平列表，前端用 parent_id 转树）。"""
        result = await self.db.execute(
            select(Department).order_by(Department.sort_order, Department.id).limit(500)
        )
        return list(result.scalars().all())

    async def get_department_for_update(self, dept_id: int) -> Department:
        """带行级锁获取部门。"""
        result = await self.db.execute(
            select(Department).where(Department.id == dept_id).with_for_update()
        )
        dept = result.scalars().first()
        if not dept:
            raise BusinessException(ErrorCode.DEPT_NOT_FOUND, f"部门不存在: {dept_id}")
        return dept

    # ============================================================
    # 创建
    # ============================================================

    async def create_department(self, body) -> Department:
        """创建部门 — 验证父部门 + 双重唯一性保护。"""
        if (await self.db.execute(select(Department).where(Department.code == body.code))).scalars().first():
            raise BusinessException(ErrorCode.DEPT_CODE_EXISTS, "部门编码已存在")

        if body.parent_id is not None:
            parent = (await self.db.execute(select(Department).where(Department.id == body.parent_id))).scalars().first()
            if not parent:
                raise BusinessException(ErrorCode.DEPT_NOT_FOUND, f"父部门不存在: {body.parent_id}")

        dept = Department(
            code=body.code, name=body.name, parent_id=body.parent_id,
            sort_order=body.sort_order, description=body.description,
        )
        self.db.add(dept)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise BusinessException(ErrorCode.DEPT_CODE_EXISTS, "部门编码已存在")
        await self.db.refresh(dept)
        return dept

    # ============================================================
    # 全量更新
    # ============================================================

    async def update_department(self, dept_id: int, body) -> Department:
        """PUT 全量更新 — 包含循环检测。"""
        dept = await self.get_department_for_update(dept_id)

        if body.parent_id is not None:
            await self._validate_parent(dept_id, body.parent_id)

        dept.name = body.name
        dept.parent_id = body.parent_id
        dept.sort_order = body.sort_order
        dept.description = body.description

        await self.db.commit()
        return dept

    # ============================================================
    # 删除
    # ============================================================

    async def delete_department(self, dept_id: int) -> dict:
        """删除部门 — 子部门变顶级 + 告知受影响用户数。"""
        dept = await self.get_department_for_update(dept_id)

        # 子部门变顶级
        children = (await self.db.execute(
            select(Department).where(Department.parent_id == dept_id).with_for_update()
        )).scalars().all()
        child_info = None
        if children:
            child_names = [c.name for c in children]
            child_info = {"count": len(children), "children": child_names}
            for child in children:
                child.parent_id = None

        # 统计受影响用户
        user_count = (await self.db.execute(
            select(func.count()).select_from(User).where(User.department_id == dept_id)
        )).scalar() or 0

        await self.db.delete(dept)
        await self.db.commit()

        parts = []
        if child_info and child_info["count"] > 0:
            parts.append(f"{child_info['count']} 个子部门已变为顶级部门")
        if user_count > 0:
            parts.append(f"{user_count} 个用户部门已清空")
        message = "已删除" + ("，" + "、".join(parts) if parts else "")

        return {
            "message": message,
            "child_depts": child_info,
            "affected_users": user_count,
        }

    # ============================================================
    # 私有 — 循环检测
    # ============================================================

    async def _validate_parent(self, dept_id: int, new_parent_id: int):
        """校验父部门存在 + 检测循环引用。"""
        if new_parent_id == dept_id:
            raise BusinessException(ErrorCode.CONFLICT, "部门不能将自己设为父部门")

        parent = (await self.db.execute(select(Department).where(Department.id == new_parent_id))).scalars().first()
        if not parent:
            raise BusinessException(ErrorCode.DEPT_NOT_FOUND, f"父部门不存在: {new_parent_id}")

        if await self._would_create_cycle(dept_id, new_parent_id):
            raise BusinessException(ErrorCode.CONFLICT, "不能将部门设置为自己的子孙部门")

    async def _would_create_cycle(self, dept_id: int, new_parent_id: int) -> bool:
        """检查 parent_id 变更是否会形成循环。沿父链向上遍历。"""
        current_id = new_parent_id
        visited: set[int] = set()
        while current_id is not None:
            if current_id == dept_id:
                return True
            if current_id in visited:
                break
            visited.add(current_id)
            result = await self.db.execute(
                select(Department.parent_id).where(Department.id == current_id)
            )
            row = result.first()
            current_id = row[0] if row else None
        return False

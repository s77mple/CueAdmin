"""部门数据访问 — 部门表 + 树形查询。"""

from sqlalchemy import select, func

from app.system.models import Department, User
from app.system.repositories.base import BaseRepository


class DepartmentRepository(BaseRepository[Department]):
    model = Department

    async def list_departments(self) -> list[Department]:
        """返回全部部门（按 sort_order 排序，前端用 parent_id 转树）。"""
        result = await self.session.execute(
            select(Department).order_by(Department.sort_order, Department.id)
        )
        return list(result.scalars().all())

    async def get_children(self, dept_id: int) -> list[Department]:
        """查直接子部门（带锁，删除时子部门变顶级用）。"""
        result = await self.session.execute(
            select(Department)
            .where(Department.parent_id == dept_id)
            .with_for_update()
        )
        return list(result.scalars().all())

    async def get_parent_id(self, dept_id: int) -> int | None:
        """查父部门 ID（循环检测沿父链遍历用）。"""
        result = await self.session.execute(
            select(Department.parent_id).where(Department.id == dept_id)
        )
        row = result.first()
        return row[0] if row else None

    async def count_users(self, dept_id: int) -> int:
        """统计该部门下的用户数（删除时提示用）。"""
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.department_id == dept_id)
        )
        return result.scalar() or 0

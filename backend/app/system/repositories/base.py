"""Repository 基类 — 通用数据访问方法。

职责边界（轻量数据访问层）：
  - 只做「查/存」：查询、session.add/delete 的对象准备
  - 不 commit、不 rollback、不抛业务异常
  - 查不到返回 None，由 Service 判断并抛 BusinessException

子类用 `model = Xxx` 指定实体，继承通用方法，再按需加语义化查询。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    model = None  # 子类覆盖为具体实体类，如 model = User

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int):
        """按主键 id 查询，查不到返回 None。"""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalars().first()

    async def get_for_update(self, id: int):
        """按主键 id 查询并加行级锁（SELECT ... FOR UPDATE）。"""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id).with_for_update()
        )
        return result.scalars().first()

    async def get_by_code(self, code: str):
        """按唯一编码 code 查询（有 code 字段的实体使用）。"""
        result = await self.session.execute(
            select(self.model).where(self.model.code == code)
        )
        return result.scalars().first()

    def add(self, obj) -> None:
        """把对象加入 session（不 commit，由 Service 控制提交时机）。"""
        self.session.add(obj)

    async def delete(self, obj) -> None:
        """把对象标记删除（不 commit，由 Service 控制提交时机）。"""
        await self.session.delete(obj)

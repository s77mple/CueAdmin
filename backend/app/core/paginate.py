"""
通用分页查询工具 — 对任意 SQLAlchemy SELECT 做 COUNT + 分页。

用法：
  stmt = select(User).options(selectinload(User.roles))
  result = await paginate(session, stmt, page=1, page_size=20)
  # result = PageData(items=[...], total=50, page=1, page_size=20, has_more=True)

分页实现要点：
  #1 COUNT 用 DISTINCT 子查询：防止 JOIN 导致重复计数
     例如按 role_id 筛选用户 → JOIN user_roles → 同一用户多角色多行
     COUNT(DISTINCT ...) 确保每个用户只算一次

  #2 数据查询也用 DISTINCT：防止 JOIN 返回重复行

  #3 参数兜底：page < 1 → 强制为 1；page_size > 100 → 强制为 100
"""

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.response import PageData


async def paginate(
    session: AsyncSession,
    stmt: Select,
    page: int,
    page_size: int,
) -> PageData:
    """#1 对任意 SELECT 语句做分页。

    不修改原始 stmt（.distinct() 和 .subquery() 返回新对象）。
    """

    # #1a 参数校验
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    # #1b COUNT — DISTINCT 后再子查询
    # 为什么：原始 stmt 可能有 JOIN，导致一行变多行
    # 先 DISTINCT（去重），再 COUNT（计数），结果准确
    count_subq = stmt.distinct().subquery()
    count_stmt = select(func.count()).select_from(count_subq)
    total = (await session.execute(count_stmt)).scalar() or 0

    # #1c 分页数据 — 同样 DISTINCT 避免重复行
    page_stmt = stmt.distinct().offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(page_stmt)
    items = list(result.scalars().all())

    # #1d 组装分页响应
    return PageData(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=page * page_size < total,  # 前端可以用这个判断要不要显示"加载更多"
    )

"""通用分页查询工具。"""

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.response import PageData


async def paginate(
    db: AsyncSession,
    stmt: Select,
    page: int,
    page_size: int,
) -> PageData:
    """对任意 SELECT 查询做分页，COUNT 用子查询避免 JOIN 重复计数。

    Args:
        db: 异步数据库会话。
        stmt: 任意 SQLAlchemy Select 语句（支持 JOIN、WHERE、ORDER BY 等，不要带 LIMIT/OFFSET）。
        page: 页码，从 1 开始。
        page_size: 每页条数。

    Returns:
        PageData: 分页结果，items 为 ORM 对象列表。
    """
    # 参数校验 — 防止非法输入
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    # COUNT — 套子查询，JOIN 时不会重复计数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # 分页数据
    page_stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(page_stmt)
    items = list(result.scalars().all())

    return PageData(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=page * page_size < total,
    )

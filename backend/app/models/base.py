"""
ORM 模型 Mixin — 为所有表自动添加时间戳字段。

每个表都会继承 TimestampMixin，自动获得：
  created_at：创建时间（数据库 DEFAULT CURRENT_TIMESTAMP）
  updated_at：更新时间（数据库 ON UPDATE CURRENT_TIMESTAMP + Python onupdate）

双重保障：
  server_default / server_onupdate → 数据库层面，raw SQL 也生效
  onupdate → ORM 层面，Python 代码也能自动更新

用法：
  class User(Base, TimestampMixin):
      ...  # 自动获得 created_at 和 updated_at
"""

from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """时间戳混入类 — 不要单独实例化，只用于继承。"""

    # created_at：只在 INSERT 时设一次，之后不再变
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # updated_at：每次 UPDATE 自动更新为当前时间
    # server_onupdate=func.now() → 数据库层面自动更新
    # onupdate=func.now()        → SQLAlchemy ORM 层面自动更新
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),    # 第一次插入时的默认值
        server_onupdate=func.now(),   # DB 层 UPDATE 时自动更新
        onupdate=func.now(),          # ORM 层 UPDATE 时自动更新
    )

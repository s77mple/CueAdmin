# ============================================================================
# Alembic 迁移环境配置
#
# 执行时机: 每次运行 `alembic upgrade head` / `alembic revision --autogenerate` 时
# 核心职责:
#   1. 告诉 Alembic 数据库在哪（同步连接 URL）
#   2. 提供目标表结构（从 Base.metadata 读取所有模型）
#   3. 选择执行模式（离线输出 SQL / 在线直接执行 DDL）
# ============================================================================

import sys, os

# 把 backend/ 加入 Python 搜索路径，确保 `app` 包可 import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logging.config import fileConfig                     # 解析 alembic.ini 中的日志配置
from sqlalchemy import create_engine, pool                # 同步引擎 + 连接池策略（DDL 必须用同步驱动）
from sqlalchemy.engine.url import make_url                 # URL 结构化解析 / 安全替换驱动名
from alembic import context                                # Alembic 运行时上下文（全局注入的模块对象）
from app.core.config import settings                       # 项目配置（读 .env）
from app.core.database import Base                         # ORM 基类，其 metadata 汇总所有模型表结构
from app.models import *  # noqa: F401, F403              # 触发所有模型类定义，自动注册到 Base.metadata

# ---- 配置对象 ----
# context.config 封装了 alembic.ini 的所有配置项
config = context.config

# ---- 同步 URL（Alembic DDL 不支持异步驱动）----
# 应用运行用 aiomysql，但 CREATE/ALTER TABLE 等底层是同步 API，
# make_url() 结构化解析后只改 drivername，避免字符串替换误改密码。
sync_url = str(
    make_url(settings.database_url)          # 例: mysql+aiomysql://root:pass@localhost/db
    .set_drivername("mysql+pymysql")         #  →  mysql+pymysql://root:pass@localhost/db
)
config.set_main_option("sqlalchemy.url", sync_url)  # 覆盖 alembic.ini 中的占位 URL

# ---- 日志初始化 ----
# 只在通过 alembic -c alembic.ini 启动时执行，不影响项目运行时日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---- 目标元数据 ----
# Alembic 对比"数据库当前状态" vs "Base.metadata 目标状态"，自动生成差异 DDL
target_metadata = Base.metadata


def run_migrations_offline():
    """离线模式：不连数据库，只输出 SQL 文本。

    用法: alembic upgrade head --sql
    场景: DBA 审核、生产环境手动执行、备份迁移脚本
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,                                          # 只传 URL 字符串，不创建连接
        target_metadata=target_metadata,                  # 目标表结构
        literal_binds=True,                               # 参数直接嵌入 SQL（:param → '值'）
    )
    with context.begin_transaction():                     # 模拟事务（输出 BEGIN/COMMIT）
        context.run_migrations()                          # 打印 SQL 到 stdout，不执行


def run_migrations_online():
    """在线模式：连接真实数据库，直接执行 DDL。

    用法: alembic upgrade head（默认）
    场景: 开发环境、CI/CD 自动部署
    """
    # 创建一次性同步引擎，迁移完立即断开（不需要连接池复用）
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,                          # 不缓存连接，用完即关
    )
    with connectable.connect() as connection:             # 建立真实数据库连接
        context.configure(
            connection=connection,                        # 用此连接执行 DDL
            target_metadata=target_metadata,              # 目标表结构
        )
        with context.begin_transaction():                 # 真实事务包裹，出错自动回滚
            context.run_migrations()                      # 发送并执行 SQL


# ---- 入口 ----
# Alembic 根据命令行参数选择模式：
#   正常执行    → run_migrations_online()
#   --sql 参数  → run_migrations_offline()
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
"""日志配置 — 基于 loguru，比标准库 logging 更简洁。

输出目标：
  stderr（终端）：开发模式 DEBUG 级别 + 彩色；生产模式 WARNING 级别
  logs/app.log：完整日志，50MB 自动切割，保留 30 天

用法：
  from app.core.logger import logger
  logger.info("用户 {} 登录成功", username)
  logger.bind(user_id=42).warning("权限不足")
"""

import sys
from loguru import logger
from app.core.config import settings

# 清空默认 handler（loguru 自带一个 stderr handler）
logger.remove()

# 终端输出
if settings.app_env == "development":
    # 开发环境：DEBUG 级别 + 彩色输出，方便调试
    logger.add(
        sys.stderr,
        level="DEBUG",
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
    )
else:
    # 生产环境：WARNING+，不打 DEBUG/INFO
    logger.add(sys.stderr, level="WARNING")

# 文件持久化 — 生产环境查问题用
logger.add(
    "logs/app.log",
    rotation="50 MB",      # 单文件 50MB 自动切新文件
    retention="30 days",   # 旧日志保留 30 天
    encoding="utf-8",
    level="DEBUG",
)

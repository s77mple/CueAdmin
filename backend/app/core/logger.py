import sys
from loguru import logger
from app.core.config import settings

logger.remove()

if settings.app_env == "development":
    logger.add(sys.stderr, level="DEBUG", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
else:
    logger.add(sys.stderr, level="WARNING")

logger.add("logs/app.log", rotation="50 MB", retention="30 days",
           encoding="utf-8", level="DEBUG")

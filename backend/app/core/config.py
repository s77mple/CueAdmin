"""
全局配置 — 通过 pydantic-settings 从 .env 文件读取。

配置读取优先级（后者覆盖前者）：
  .env 文件  →  系统环境变量  →  代码默认值

用法：
  from app.core.config import settings
  settings.database_url  # 自动从 .env 读取

为什么用 pydantic-settings 而不是 os.environ？
  - 类型校验（database_url 必须是合法连接串）
  - 启动时 validate_secrets() 兜底检查
  - .env 文件自动加载，开发/部署时改配置文件就行
"""

import os
from pydantic_settings import BaseSettings
from sqlalchemy.engine.url import make_url

# 自动定位 backend/.env 文件
_ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")


class Settings(BaseSettings):
    """应用配置 — 所有环境相关的变量都在这。"""

    # ---- 数据库 ----
    # 格式: mysql+aiomysql://user:pass@host:port/dbname
    database_url: str = ""   # 空字符串 = 未配置，启动时 validate_secrets 会报错

    # ---- JWT ----
    jwt_secret: str = ""     # 签名密钥，生产环境必须改，且不要硬编码
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15   # access token 15 分钟后过期（短命，丢了损失小）
    jwt_refresh_expire_days: int = 7      # refresh token 7 天后过期（长命，用于换新 access）

    # ---- Redis ----
    redis_url: str = "redis://localhost:6379/0"

    # ---- 应用 ----
    app_name: str = "CueAdmin"
    app_env: str = "development"  # development → DEBUG 日志；production → WARNING+
    debug: bool = True

    model_config = {
        "env_file": _ENV_FILE,          # .env 文件路径
        "env_file_encoding": "utf-8",
        "extra": "ignore",              # .env 里多了不认识的环境变量不报错
    }

    def validate_secrets(self):
        """启动时校验 — 防止用默认空值启动，导致 JWT 被轻易破解。"""
        missing = []
        if not self.database_url:
            missing.append("DATABASE_URL")
        else:
            # 校验连接串格式
            try:
                make_url(self.database_url)
            except Exception:
                raise RuntimeError(
                    f"DATABASE_URL 格式无效: {self.database_url[:50]}..."
                ) from None
        if not self.jwt_secret or self.jwt_secret == "change-me-to-a-random-secret-string":
            missing.append("JWT_SECRET")
        if missing:
            raise RuntimeError(
                f"以下配置未设置，请在 backend/.env 中配置: {', '.join(missing)}"
            )


# 全局单例 — 模块加载时自动读取 .env
settings = Settings()

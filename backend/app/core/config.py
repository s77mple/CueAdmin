"""
全局配置，通过 pydantic-settings 从 .env 文件读取。

每个字段的读取顺序：
    .env 文件 > 系统环境变量 > 代码默认值
"""
import os
from pydantic_settings import BaseSettings
from sqlalchemy.engine.url import make_url

_ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")


class Settings(BaseSettings):
    # ====== 数据库 ======
    database_url: str = ""  # 必须在 .env 中配置

    # ====== JWT ======
    jwt_secret: str = ""   # 必须在 .env 中配置，否则启动报错
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # ====== Redis ======
    redis_url: str = "redis://localhost:6379/0"

    # ====== 应用 ======
    app_name: str = "CueAdmin"
    app_env: str = "development"
    debug: bool = True

    model_config = {
        "env_file": _ENV_FILE,
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def validate_secrets(self):
        """启动时校验：未配置的 secret 直接报错，防止用默认值启动。"""
        missing = []
        if not self.database_url:
            missing.append("DATABASE_URL")
        else:
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


settings = Settings()

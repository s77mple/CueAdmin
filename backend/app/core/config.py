"""
全局配置，通过 pydantic-settings 从 .env 文件读取。

每个字段的读取顺序：
    .env 文件 > 系统环境变量 > 代码默认值
"""
import os
from pydantic_settings import BaseSettings

_ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")


class Settings(BaseSettings):
    # ====== 数据库 ======
    database_url: str = "mysql+aiomysql://root:password@localhost:3306/mydb"

    # ====== JWT ======
    jwt_secret: str = "change-me-to-a-random-secret-string"
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


settings = Settings()

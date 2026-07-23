"""认证相关 Schema"""

from pydantic import BaseModel
from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    username: str
    password: str
    client: str | None = None  # "miniapp" or "admin"


class LoginResponse(BaseModel):
    access_token: str
    user: "UserRead"
    permissions: list[str]
    menus: list[dict] = []

    model_config = {"from_attributes": True}


class MeResponse(BaseModel):
    user: "UserRead"
    permissions: list[str]
    roles: list[dict]
    menus: list[dict]

    model_config = {"from_attributes": True}

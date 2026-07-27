"""认证相关 Schema"""

from pydantic import BaseModel

from app.schemas.response import ApiResponse
from app.schemas.role import RoleBrief
from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    username: str
    password: str
    client: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    user: "UserRead"
    permissions: list[str]
    roles: list[RoleBrief] = []
    menus: list[dict] = []

    model_config = {"from_attributes": True}


class MeResponse(BaseModel):
    user: "UserRead"
    permissions: list[str]
    roles: list[RoleBrief]
    menus: list[dict]

    model_config = {"from_attributes": True}


# —————— 响应类型 ——————
class LoginApiResponse(ApiResponse[LoginResponse]):
    pass


class MeApiResponse(ApiResponse[MeResponse]):
    pass

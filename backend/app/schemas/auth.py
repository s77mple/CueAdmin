"""认证相关 Schema"""

from pydantic import BaseModel, Field

from app.schemas.response import ApiResponse
from app.schemas.role import RoleBrief
from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="用户名")
    password: str = Field(..., min_length=1, max_length=128, description="密码")
    client: str | None = Field(None, max_length=50, description="客户端标识")


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

"""用户 Schema"""

from datetime import datetime
from pydantic import BaseModel, field_validator


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str
    phone: str | None = None
    role_ids: list[int] = []

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("用户名至少 3 个字符")
        if v != v.strip():
            raise ValueError("用户名不允许首尾包含空格")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码至少 6 个字符")
        return v


class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    display_name: str | None = None
    phone: str | None = None
    is_active: bool | None = None
    role_ids: list[int] | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) < 3:
            raise ValueError("用户名至少 3 个字符")
        if v != v.strip():
            raise ValueError("用户名不允许首尾包含空格")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) < 6:
            raise ValueError("密码至少 6 个字符")
        return v


class UserRead(BaseModel):
    id: int
    username: str
    display_name: str
    phone: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# —————— 响应类型（具体类继承，绕开泛型 response_model 坑）——————
from app.schemas.response import ApiResponse, PageData


class UserReadResponse(ApiResponse[UserRead]):
    pass


class UserListResponse(ApiResponse[PageData[UserRead]]):
    pass

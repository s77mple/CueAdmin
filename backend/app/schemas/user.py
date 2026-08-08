"""用户 Schema"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=50)
    phone: str | None = Field(None, max_length=20, pattern=r"^1[3-9]\d{9}$")
    role_ids: list[int] = Field(default=[], max_length=100)
    department_id: int | None = None

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

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        import re
        if v is not None and not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确")
        return v


class UserUpdate(BaseModel):
    """全量更新（PUT）—— 除 password 外所有字段必传，可空字段传 null（password 不传则保持原密码）"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str | None = Field(None, min_length=6, max_length=128, description="密码，留空不修改")
    display_name: str = Field(..., min_length=1, max_length=50, description="显示名")
    phone: str | None = Field(..., max_length=20, pattern=r"^1[3-9]\d{9}$", description="手机号，无则传 null")
    is_active: bool = Field(..., description="是否启用")
    role_ids: list[int] = Field(..., max_length=100, description="角色 ID 列表，可为空数组")
    department_id: int | None = Field(..., description="部门 ID，无则传 null")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if v != v.strip():
            raise ValueError("用户名不允许首尾包含空格")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        import re
        if v is not None and not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确")
        return v


class UserPatch(BaseModel):
    """部分更新（PATCH）—— 仅传需要修改的字段"""
    username: str | None = Field(None, min_length=3, max_length=50)
    password: str | None = Field(None, min_length=6, max_length=128)
    display_name: str | None = Field(None, min_length=1, max_length=50)
    phone: str | None = Field(None, max_length=20, pattern=r"^1[3-9]\d{9}$")
    is_active: bool | None = None
    role_ids: list[int] | None = Field(None, max_length=100)
    department_id: int | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if v != v.strip():
            raise ValueError("用户名不允许首尾包含空格")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        import re
        if v is not None and not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确")
        return v


class RoleBrief(BaseModel):
    id: int
    code: str
    name: str

    model_config = {"from_attributes": True}


class UserRead(BaseModel):
    id: int
    username: str
    display_name: str
    phone: str | None = None
    is_active: bool
    department_id: int | None = None
    roles: list[RoleBrief] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# —————— 响应类型（具体类继承，绕开泛型 response_model 坑）——————
from app.schemas.response import ApiResponse, PageData


class UserReadResponse(ApiResponse[UserRead]):
    pass


class UserListResponse(ApiResponse[PageData[UserRead]]):
    pass

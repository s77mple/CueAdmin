"""用户 Schema — 创建/更新/查询的数据结构。

三种 Schema 模式（本项目所有实体通用）：

  XxxCreate  → POST 创建时的请求体（必填字段 = Field(...)）
  XxxUpdate  → PUT 全量更新（所有字段必填，可空字段传 null）
  XxxPatch   → PATCH 部分更新（所有字段可选，传了才改）
  XxxRead    → 响应体（查询返回的字段）

为什么分 Create / Update / Patch？
  - Create：密码必传，username 不能改
  - Update：密码可选（不传不改），username 可能变了
  - Patch：所有字段都 optional，前端只传要改的字段
"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from app.schemas.role import RoleBrief


# ============================================================
# 1. UserCreate — 创建用户
# ============================================================

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名，至少 3 个字符")
    password: str = Field(..., min_length=6, max_length=128, description="密码，至少 6 个字符")
    display_name: str = Field(..., min_length=1, max_length=50, description="显示名")
    phone: str | None = Field(None, max_length=20, pattern=r"^1[3-9]\d{9}$", description="手机号，无则不传")
    role_ids: list[int] = Field(default=[], max_length=100, description="角色 ID 列表，可为空数组")     # 允许创建无角色用户
    department_id: int | None = Field(None, description="部门 ID，无则不传")

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


# ============================================================
# 2. UserUpdate — 全量更新（PUT）
# ============================================================

class UserUpdate(BaseModel):
    """PUT 全量更新 — password 为空不修改，其余字段全量覆盖。"""
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


# ============================================================
# 3. UserPatch — 部分更新（PATCH）
# ============================================================

class UserPatch(BaseModel):
    """PATCH 部分更新 — 所有字段都 Optional。

    model_dump(exclude_unset=True) 是关键：
      前端只传 { is_active: false }
      → data = {"is_active": False}
      → API 层只改 is_active，其他字段不动
    """
    username: str | None = Field(None, min_length=3, max_length=50, description="用户名")
    password: str | None = Field(None, min_length=6, max_length=128, description="密码")
    display_name: str | None = Field(None, min_length=1, max_length=50, description="显示名")
    phone: str | None = Field(None, max_length=20, pattern=r"^1[3-9]\d{9}$", description="手机号")
    is_active: bool | None = Field(None, description="是否启用")
    role_ids: list[int] | None = Field(None, max_length=100, description="角色 ID 列表，传 [] 清空角色")        # None = 没传，[] = 清空角色
    department_id: int | None = Field(None, description="部门 ID")

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


# ============================================================
# 4. 辅助 Schema（RoleBrief 统一用 app.schemas.role 的，不重复定义）
# ============================================================

# ============================================================
# 5. UserRead — 查询响应体
# ============================================================

class UserRead(BaseModel):
    """用户查询返回的字段。"""
    id: int
    username: str
    display_name: str
    phone: str | None = None
    is_active: bool
    department_id: int | None = None
    roles: list[RoleBrief] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}  # 允许从 ORM 对象自动转换


# ============================================================
# 6. 响应包装类型
# ============================================================

from app.schemas.response import ApiResponse, PageData


class UserReadResponse(ApiResponse[UserRead]):
    """单用户响应：GET /users/{id}、POST /users、PUT /users/{id}"""
    pass


class UserListResponse(ApiResponse[PageData[UserRead]]):
    """用户列表响应：GET /users"""
    pass

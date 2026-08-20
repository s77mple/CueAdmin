"""用户 Schema — 创建/更新/查询的数据结构。

三种 Schema 模式（本项目所有实体通用）：

  XxxCreate  → POST 创建时的请求体（必填字段不设默认值）
  XxxUpdate  → PUT 全量更新（所有字段必填，可空字段传 null）
  XxxPatch   → PATCH 部分更新（所有字段可选，传了才改）
  XxxRead    → 响应体（查询返回的字段）

为什么分 Create / Update / Patch？
  - Create：密码必传，username 不能改
  - Update：全量覆盖（所有字段必传），username 可能变了
  - Patch：所有字段都 optional，前端只传要改的字段
"""

import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

from app.schemas.role import RoleBrief


# ============================================================
# 校验函数 — 三个 Schema 共用，统一抛 PydanticCustomError 出中文报错
#
# 为什么不写在 Field(min_length=...) 里？
#   Field 的长度约束报的是英文原始错误（"String should have at least 3
#   characters"），对终端用户不友好；而且会先于 field_validator 执行，
#   让 validator 里的中文报错永远轮不到。所以长度/格式校验统一挪到这里。
# ============================================================

def _validate_username(v: str) -> str:
    """用户名 — 3~50 字符，不允许首尾空格。"""
    if len(v) < 3:
        raise PydanticCustomError("username_too_short", "用户名至少 3 个字符")
    if len(v) > 50:
        raise PydanticCustomError("username_too_long", "用户名最多 50 个字符")
    if v != v.strip():
        raise PydanticCustomError("username_whitespace", "用户名不允许首尾包含空格")
    return v


def _validate_password(v: str) -> str:
    """密码 — 6~128 字符。"""
    if len(v) < 6:
        raise PydanticCustomError("password_too_short", "密码至少 6 个字符")
    if len(v) > 128:
        raise PydanticCustomError("password_too_long", "密码最多 128 个字符")
    return v


def _validate_display_name(v: str) -> str:
    """显示名 — 1~50 字符。"""
    if len(v) < 1:
        raise PydanticCustomError("display_name_empty", "显示名不能为空")
    if len(v) > 50:
        raise PydanticCustomError("display_name_too_long", "显示名最多 50 个字符")
    return v


def _validate_phone(v: str) -> str:
    """手机号 — 11 位数字，1 开头。"""
    if not re.match(r"^1[3-9]\d{9}$", v):
        raise PydanticCustomError("phone_format", "手机号格式不正确")
    return v


# ============================================================
# 1. UserCreate — 创建用户
# ============================================================

class UserCreate(BaseModel):
    username: Annotated[str, Field(description="用户名，至少 3 个字符")]
    password: Annotated[str, Field(description="密码，至少 6 个字符")]
    display_name: Annotated[str, Field(description="显示名")]
    phone: Annotated[str | None, Field(description="手机号，无则不传")] = None
    role_ids: Annotated[list[int], Field(default_factory=list, max_length=100, description="角色 ID 列表，可为空数组")]  # 允许创建无角色用户
    department_id: Annotated[int | None, Field(description="部门 ID，无则不传")] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return _validate_username(v)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password(v)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        return _validate_display_name(v)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_phone(v)


# ============================================================
# 2. UserUpdate — 全量更新（PUT）
# ============================================================

class UserUpdate(BaseModel):
    """PUT 全量更新 — 所有字段覆盖写入。"""
    username: Annotated[str, Field(description="用户名")]
    display_name: Annotated[str, Field(description="显示名")]
    phone: Annotated[str | None, Field(description="手机号，无则传 null")]
    is_active: Annotated[bool, Field(description="是否启用")]
    role_ids: Annotated[list[int], Field(max_length=100, description="角色 ID 列表，可为空数组")]
    department_id: Annotated[int | None, Field(description="部门 ID，无则传 null")]

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return _validate_username(v)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str) -> str:
        return _validate_display_name(v)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_phone(v)


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
    username: Annotated[str | None, Field(description="用户名")] = None
    display_name: Annotated[str | None, Field(description="显示名")] = None
    phone: Annotated[str | None, Field(description="手机号")] = None
    is_active: Annotated[bool | None, Field(description="是否启用")] = None
    role_ids: Annotated[list[int] | None, Field(max_length=100, description="角色 ID 列表，传 [] 清空角色")] = None  # None = 没传，[] = 清空角色
    department_id: Annotated[int | None, Field(description="部门 ID")] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_username(v)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_display_name(v)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_phone(v)


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
    roles: Annotated[list[RoleBrief], Field(default_factory=list)]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

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

校验策略（本项目统一）：
  - 长度/格式规则直接写在 Field(min_length/max_length/pattern) 上
    → 自动进 OpenAPI 文档 + pydantic-core（Rust）里执行，快
  - Field 表达不了的复杂规则才用 field_validator
    （如 username 不允许首尾空格：strip 逻辑 Field 无法声明）
  - 前端已用 el-form rules 做主要校验，后端只兜底防非法请求
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

from app.schemas.role import RoleBrief


# ============================================================
# 校验函数 — 只放 Field 表达不了的复杂规则
# ============================================================

def _validate_username(v: str) -> str:
    """用户名 — 不允许首尾空格（长度 3~50 已由 Field 覆盖）。"""
    if v != v.strip():
        raise PydanticCustomError("username_whitespace", "用户名不允许首尾包含空格")
    return v


# ============================================================
# 1. UserCreate — 创建用户
# ============================================================

class UserCreate(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=50, description="用户名")]
    password: Annotated[str, Field(min_length=6, max_length=128, description="密码")]
    display_name: Annotated[str, Field(min_length=1, max_length=50, description="显示名")]
    phone: Annotated[str | None, Field(pattern=r"^1[3-9]\d{9}$", description="手机号，无则不传")] = None
    role_ids: Annotated[list[int], Field(default_factory=list, max_length=100, description="角色 ID 列表，可为空数组")]  # 允许创建无角色用户
    department_id: Annotated[int | None, Field(description="部门 ID，无则不传")] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return _validate_username(v)


# ============================================================
# 2. UserUpdate — 全量更新（PUT）
# ============================================================

class UserUpdate(BaseModel):
    """PUT 全量更新 — 所有字段覆盖写入。"""
    username: Annotated[str, Field(min_length=3, max_length=50, description="用户名")]
    display_name: Annotated[str, Field(min_length=1, max_length=50, description="显示名")]
    phone: Annotated[str | None, Field(pattern=r"^1[3-9]\d{9}$", description="手机号，无则传 null")]
    is_active: Annotated[bool, Field(description="是否启用")]
    role_ids: Annotated[list[int], Field(max_length=100, description="角色 ID 列表，可为空数组")]
    department_id: Annotated[int | None, Field(description="部门 ID，无则传 null")]

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return _validate_username(v)


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
    username: Annotated[str | None, Field(min_length=3, max_length=50, description="用户名")] = None
    display_name: Annotated[str | None, Field(min_length=1, max_length=50, description="显示名")] = None
    phone: Annotated[str | None, Field(pattern=r"^1[3-9]\d{9}$", description="手机号")] = None
    is_active: Annotated[bool | None, Field(description="是否启用")] = None
    role_ids: Annotated[list[int] | None, Field(max_length=100, description="角色 ID 列表，传 [] 清空角色")] = None  # None = 没传，[] = 清空角色
    department_id: Annotated[int | None, Field(description="部门 ID")] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_username(v)


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

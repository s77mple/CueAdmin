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

from app.system.schemas.role import RoleBrief
from app.system.schemas.department import DepartmentBrief



# 校验函数 — 只放 Field 表达不了的复杂规则

def _validate_username(v: str) -> str:
    """用户名 — 不允许首尾空格（长度 3~50 已由 Field 覆盖）。"""
    if v != v.strip():
        raise PydanticCustomError("username_whitespace", "用户名不允许首尾包含空格")
    return v


# UserCreate — 创建用户

class UserCreate(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=50, description="用户名")]
    password: Annotated[str, Field(min_length=6, max_length=128, description="密码")]
    display_name: Annotated[str, Field(min_length=1, max_length=50, description="显示名")]
    phone: Annotated[str | None, Field(pattern=r"^1[3-9]\d{9}$", description="手机号")] = None
    role_ids: Annotated[list[int], Field(default_factory=list, max_length=100, description="角色 ID 列表")]
    department_id: Annotated[int | None, Field(description="部门 ID")] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return _validate_username(v)


# UserUpdate — 全量更新（PUT）

class UserUpdate(BaseModel):
    """PUT 全量更新 — 所有字段覆盖写入。"""
    username: Annotated[str, Field(min_length=3, max_length=50, description="用户名")]
    display_name: Annotated[str, Field(min_length=1, max_length=50, description="显示名")]
    phone: Annotated[str | None, Field(pattern=r"^1[3-9]\d{9}$", description="手机号")]
    is_active: Annotated[bool, Field(description="是否启用")]
    role_ids: Annotated[list[int], Field(max_length=100, description="角色 ID 列表")]
    department_id: Annotated[int | None, Field(description="部门 ID")]

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return _validate_username(v)


# UserPatch — 部分更新（PATCH）

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
    role_ids: Annotated[list[int] | None, Field(max_length=100, description="角色 ID 列表")] = None
    department_id: Annotated[int | None, Field(description="部门 ID")] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_username(v)


# UserRead vs UserListItem — 学 RuoYi：接口职责分离，各自 schema 只写真实返回的字段。
#   - UserRead（UserDetail.user / 写返回 / 登录 user）：回显 + 认证场景。编辑弹窗回显
#     勾选要的是 id —— department_id / role_ids；表格渲染要的嵌套对象 department / roles
#     后端在这类响应里不返回，所以 UserRead 不声明它们（那归 UserListItem）。
#   - UserListItem（PageData[UserListItem]）：列表行 = 渲染名字对象（department / roles）
#     + 行内 department_id（RuoYi 行里就带 deptId）；role_ids 不进列表，
#     勾选回显只发生在编辑弹窗，由 UserRead 承担。
# 需要 role 的 permissions/menus 时用 RoleItem（见 schemas/role.py），不在这里外溢。
#
# 纪律：response 字段一律不加 = None / default_factory 默认值 → OpenAPI 文档里全部「必返」；
# null / 空列表是合法值，用类型表达（str | None、list[T]），不带默认值 ≠ 不可为空。

class UserRead(BaseModel):
    """用户信息（单查回显 / 写返回 / 登录响应共用）— 字段与这三个接口真实返回一一对应。"""
    id: Annotated[int, Field(description="用户 ID")]
    username: Annotated[str, Field(description="用户名")]
    display_name: Annotated[str, Field(description="显示名")]
    phone: Annotated[str | None, Field(description="手机号（未填写时为 null）")]
    is_active: Annotated[bool, Field(description="是否启用")]
    department_id: Annotated[int | None, Field(description="部门 ID")]
    role_ids: Annotated[list[int], Field(description="角色 ID 列表")]
    created_at: Annotated[datetime, Field(description="创建时间")]
    updated_at: Annotated[datetime, Field(description="更新时间")]

    model_config = {"from_attributes": True}


# UserListItem — 列表专用瘦行（GET /users 分页返回）

class UserListItem(BaseModel):
    """用户列表行 — 表格要渲染的字段 + 行内 id。

    学 RuoYi：列表行带嵌套对象（department / roles，管表格「部门」列 / 「角色」tag 列渲染），
    同时行内带 department_id（RuoYi 的 deptId 就下发行里）供行级操作直接用；
    role_ids 仍不进列表（回显勾选只发生在编辑弹窗，由单查接口的 UserRead 承担）。
    """
    id: Annotated[int, Field(description="用户 ID")]
    username: Annotated[str, Field(description="用户名")]
    display_name: Annotated[str, Field(description="显示名")]
    phone: Annotated[str | None, Field(description="手机号")]
    is_active: Annotated[bool, Field(description="是否启用")]
    department_id: Annotated[int | None, Field(description="部门 ID（行内 id，学 RuoYi 下发行带 deptId）")]
    department: Annotated[DepartmentBrief | None, Field(description="部门对象（表格「部门」列显示名字用）")]
    roles: Annotated[list[RoleBrief], Field(description="角色对象列表（表格「角色」tag 列渲染用）")]
    created_at: Annotated[datetime, Field(description="创建时间")]
    updated_at: Annotated[datetime, Field(description="更新时间")]

    model_config = {"from_attributes": True}


class UserDetail(BaseModel):
    """用户详情响应 — 单查接口 GET /users/{id} 返回。

    学 RuoYi 的 getInfo：一次返回「用户详情 + 全量角色下拉」；
    部门下拉/部门树不进详情（列表页级需求），前端独立调 GET /departments/tree。
    """
    user: Annotated[UserRead, Field(description="用户详情")]
    roles: Annotated[list[RoleBrief], Field(description="全量角色列表（下拉框用）")]

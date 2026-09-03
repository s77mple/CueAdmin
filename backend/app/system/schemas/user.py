"""用户 Schema — 请求体（入参）与响应体（出参）。

全项目命名约定：XxxCreate / XxxUpdate / XxxPatch 是请求体；
XxxRead 是响应体基名，具体响应按接口职责派生 —— 本文件：
UserRead（回显）/ UserListItem（列表行）/ UserDetail（编辑回显）。
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

from app.system.schemas.role import RoleBrief
from app.system.schemas.department import DepartmentBrief
from app.system.schemas.post import PostBrief



# 校验函数 — 只放 Field 表达不了的复杂规则

def _validate_username(v: str) -> str:
    """用户名 — 不允许首尾空格（长度 3~50 已由 Field 覆盖）。"""
    if v != v.strip():
        raise PydanticCustomError("username_whitespace", "用户名不允许首尾包含空格")
    return v


# ===== 请求体（入参）=====

# UserCreate — POST 新建

class UserCreate(BaseModel):
    username: Annotated[str, Field(min_length=3, max_length=50, description="用户名")]
    password: Annotated[str, Field(min_length=6, max_length=128, description="密码")]
    display_name: Annotated[str, Field(min_length=1, max_length=50, description="显示名")]
    phone: Annotated[str | None, Field(pattern=r"^1[3-9]\d{9}$", description="手机号")] = None
    role_ids: Annotated[list[int], Field(default_factory=list, max_length=100, description="角色 ID 列表")]
    post_ids: Annotated[list[int], Field(default_factory=list, max_length=100, description="岗位 ID 列表")]
    department_id: Annotated[int | None, Field(description="部门 ID")] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return _validate_username(v)


# UserUpdate — PUT 全量覆盖

class UserUpdate(BaseModel):
    """PUT 全量更新 — 所有字段覆盖写入。"""
    username: Annotated[str, Field(min_length=3, max_length=50, description="用户名")]
    display_name: Annotated[str, Field(min_length=1, max_length=50, description="显示名")]
    phone: Annotated[str | None, Field(pattern=r"^1[3-9]\d{9}$", description="手机号")]
    is_active: Annotated[bool, Field(description="是否启用")]
    role_ids: Annotated[list[int], Field(max_length=100, description="角色 ID 列表")]
    post_ids: Annotated[list[int], Field(max_length=100, description="岗位 ID 列表")]
    department_id: Annotated[int | None, Field(description="部门 ID")]

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return _validate_username(v)


# UserPatch — PATCH 部分更新

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
    post_ids: Annotated[list[int] | None, Field(max_length=100, description="岗位 ID 列表")] = None
    department_id: Annotated[int | None, Field(description="部门 ID")] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return _validate_username(v)


# ===== 响应体（出参）=====

#   UserRead     回显（详情.user / 写返回 / 登录 user）— 纯列镜像，无 role_ids / post_ids
#   UserListItem 列表行 — 表格渲染要的 department 名字对象 + 行内 department_id（学 RuoYi 列表行不下发角色）
#   UserDetail   编辑回显 — user + 全量下拉 roles/posts + 已分配 role_ids/post_ids（getInfo 顶层同款）
# role_ids / post_ids 装配只在 get_user_detail 一处现算；role 完整对象用 RoleItem，post 用 PostItem。
#
# 纪律：response 字段一律不加 = None / default_factory → OpenAPI 里全部必返；可空用类型表达（str | None、list[T]）

class UserRead(BaseModel):
    """用户信息 — 回显（详情.user / 写返回 / 登录 user 共用），纯列镜像无 role_ids。"""
    id: Annotated[int, Field(description="用户 ID")]
    username: Annotated[str, Field(description="用户名")]
    display_name: Annotated[str, Field(description="显示名")]
    phone: Annotated[str | None, Field(description="手机号")]
    is_active: Annotated[bool, Field(description="是否启用")]
    department_id: Annotated[int | None, Field(description="部门 ID")]
    created_at: Annotated[datetime, Field(description="创建时间")]
    updated_at: Annotated[datetime, Field(description="更新时间")]

    model_config = {"from_attributes": True}


class UserListItem(BaseModel):
    """用户列表行 — 学 RuoYi 列表行不带角色：department 名字对象 + 行内 department_id，不含 role_ids/roles（回显走详情）。"""
    id: Annotated[int, Field(description="用户 ID")]
    username: Annotated[str, Field(description="用户名")]
    display_name: Annotated[str, Field(description="显示名")]
    phone: Annotated[str | None, Field(description="手机号")]
    is_active: Annotated[bool, Field(description="是否启用")]
    department_id: Annotated[int | None, Field(description="部门 ID")]
    department: Annotated[DepartmentBrief | None, Field(description="所属部门")]
    created_at: Annotated[datetime, Field(description="创建时间")]
    updated_at: Annotated[datetime, Field(description="更新时间")]

    model_config = {"from_attributes": True}


class UserDetail(BaseModel):
    """用户详情（编辑回显，getInfo 同款）— user 纯列 + 全量下拉 roles/posts + 已分配 role_ids/post_ids。

    roles/posts = 全部可选角色/岗位（下拉选项），role_ids/post_ids = 当前已分配（勾选回显）。
    角色管权限、岗位只做标签，两条 M2M 同构；部门树走列表页 /departments/tree。
    """
    user: Annotated[UserRead, Field(description="用户信息")]
    roles: Annotated[list[RoleBrief], Field(description="全部角色")]
    role_ids: Annotated[list[int], Field(description="已分配角色 ID")]
    posts: Annotated[list[PostBrief], Field(description="全部岗位")]
    post_ids: Annotated[list[int], Field(description="已分配岗位 ID")]

"""部门 Schema — 创建/更新/查询的数据结构。

部门管理的特点：
  - 树形结构（与菜单相同的自引用模式）
  - 删除部门 → 子部门变顶级（SET NULL）
  - 删除部门 → 用户的 department_id 变 NULL（SET NULL）
  - 不允许产生循环引用
"""

from typing import Annotated

from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    code: Annotated[str, Field(
        min_length=1, max_length=50,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="部门编码，创建后不可修改，小写字母开头，仅含小写字母/数字/下划线",
    )]
    name: Annotated[str, Field(min_length=1, max_length=50, description="部门名称")]
    parent_id: Annotated[int | None, Field(description="父部门 ID")] = None  # null = 顶级部门
    sort_order: Annotated[int, Field(ge=0, description="排序号，越小越靠前")] = 0
    description: Annotated[str | None, Field(max_length=500, description="描述")] = None


class DepartmentUpdate(BaseModel):
    """PUT 全量更新 — code 不可修改，其余所有字段必传。"""
    name: Annotated[str, Field(min_length=1, max_length=50, description="部门名称")]
    parent_id: Annotated[int | None, Field(description="父部门 ID")]
    sort_order: Annotated[int, Field(ge=0, description="排序号")]
    description: Annotated[str | None, Field(max_length=500, description="描述")]


# 响应 Schema

class DepartmentItem(BaseModel):
    """部门列表项 — 扁平列表，前端转树。"""
    id: Annotated[int, Field(description="部门 ID")]
    code: Annotated[str, Field(description="部门编码")]
    name: Annotated[str, Field(description="部门名称")]
    parent_id: Annotated[int | None, Field(description="父部门 ID")]
    sort_order: Annotated[int, Field(description="排序号")]
    description: Annotated[str | None, Field(description="描述")]

    model_config = {"from_attributes": True}


class DepartmentListResponse(BaseModel):
    items: Annotated[list[DepartmentItem], Field(description="部门列表")]
    total: Annotated[int, Field(description="总条数")]


class DepartmentBrief(BaseModel):
    """部门简要信息 — 嵌套在用户响应中。"""
    id: Annotated[int, Field(description="部门 ID")]
    code: Annotated[str, Field(description="部门编码")]
    name: Annotated[str, Field(description="部门名称")]
    parent_id: Annotated[int | None, Field(description="父部门 ID")]

    model_config = {"from_attributes": True}


class DepartmentTreeNode(BaseModel):
    """部门树节点 — GET /departments/tree 返回的嵌套组织架构。

    注意：本文件没有 ``from __future__ import annotations``，
    自引用 children 必须用带引号的 ForwardRef，pydantic v2 会在模块
    命名空间里延迟解析。若报 model_rebuild 错，在类定义后补一行
    ``DepartmentTreeNode.model_rebuild()``。
    """

    id: Annotated[int, Field(description="部门 ID")]
    code: Annotated[str, Field(description="部门编码")]
    name: Annotated[str, Field(description="部门名称")]
    parent_id: Annotated[int | None, Field(description="父部门 ID")]
    sort_order: Annotated[int, Field(description="排序号")]
    description: Annotated[str | None, Field(description="描述")]
    children: Annotated[
        list["DepartmentTreeNode"],
        Field(description="子部门，叶子为空列表"),
    ]

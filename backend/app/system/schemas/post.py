"""岗位 Schema — 请求体（入参）与响应体（出参）。

命名约定（同 user.py）：XxxCreate / XxxUpdate 是请求体；
响应：PostItem（列表/单查行）嵌用户响应（UserDetail.posts 全量下拉）用 PostBrief。
"""

from typing import Annotated

from pydantic import BaseModel, Field


# ===== 请求体（入参）=====

# PostCreate — POST 新建

class PostCreate(BaseModel):
    code: Annotated[str, Field(
        min_length=1, max_length=50,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="岗位编码，创建后不可修改，小写字母开头，仅含小写字母/数字/下划线",
    )]
    name: Annotated[str, Field(min_length=1, max_length=50, description="岗位名称")]
    sort_order: Annotated[int, Field(ge=0, description="排序号，越小越靠前")] = 0
    description: Annotated[str | None, Field(max_length=200, description="描述")] = None


# PostUpdate — PUT 全量覆盖

class PostUpdate(BaseModel):
    """PUT 全量更新 — code 不可修改，其余所有字段必传。"""
    name: Annotated[str, Field(min_length=1, max_length=50, description="岗位名称")]
    sort_order: Annotated[int, Field(ge=0, description="排序号，越小越靠前")]
    description: Annotated[str | None, Field(max_length=200, description="描述")]


# ===== 响应体（出参）=====

#   PostItem  岗位行（列表 + 单查回显）
#   PostBrief 岗位简要（嵌用户响应 UserDetail.posts，下拉选项用）
#
# 纪律：response 字段一律不加 = None / default_factory → OpenAPI 里全部必返；可空用类型表达（str | None）

class PostItem(BaseModel):
    """岗位行 — GET /posts 列表项 + GET /posts/{id} 回显共用。"""
    id: Annotated[int, Field(description="岗位 ID")]
    code: Annotated[str, Field(description="岗位编码")]
    name: Annotated[str, Field(description="岗位名称")]
    sort_order: Annotated[int, Field(description="排序号")]
    description: Annotated[str | None, Field(description="描述")]

    model_config = {"from_attributes": True}


class PostBrief(BaseModel):
    """岗位简要 — 嵌套在用户响应中（编辑弹窗的全量下拉选项）。"""
    id: Annotated[int, Field(description="岗位 ID")]
    code: Annotated[str, Field(description="岗位编码")]
    name: Annotated[str, Field(description="岗位名称")]

    model_config = {"from_attributes": True}

"""统一响应结构 — 所有 API 返回的 JSON 格式都一样。"""

from typing import Annotated

from pydantic import BaseModel, Field


class ApiResponse[T](BaseModel):
    """通用响应包装 — 所有 API 都用这个返回。"""

    code: Annotated[int, Field(description="响应码，0 表示成功，非 0 为错误码")]
    message: Annotated[str, Field(description="提示信息")]
    data: Annotated[T | None, Field(description="业务数据")]

    @classmethod
    def ok(cls, data: T | None = None, message: str = "操作成功") -> "ApiResponse[T]":
        """快捷创建成功响应。"""
        return cls(code=0, message=message, data=data)

    @classmethod
    def fail(cls, code: int, message: str) -> "ApiResponse[None]":
        """快捷创建失败响应。"""
        return cls(code=code, message=message, data=None)


class PageData[T](BaseModel):
    """分页响应 — 列表接口专用。

    前端拿到后：
      items → 表格数据
      total → 分页组件显示总条数
      page / page_size → 当前页码和每页条数
      has_more → 是否还有下一页（可用来判断要不要继续加载）
    """

    items: Annotated[list[T], Field(description="当前页数据列表")]
    total: Annotated[int, Field(description="总条数")]
    page: Annotated[int, Field(description="当前页码")]
    page_size: Annotated[int, Field(description="每页条数")]
    has_more: Annotated[bool, Field(description="是否还有下一页")]

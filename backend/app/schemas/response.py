"""统一响应结构 — 泛型，所有接口复用。"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "操作成功"
    data: T | None = None
    details: dict = Field(default_factory=dict)

    @classmethod
    def ok(cls, data: T | None = None, message: str = "操作成功") -> "ApiResponse[T]":
        return cls(code=0, message=message, data=data)

    @classmethod
    def fail(cls, code: int, message: str, details: dict | None = None) -> "ApiResponse":
        return cls(code=code, message=message, data=None, details=details or {})


class PageData(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_more: bool

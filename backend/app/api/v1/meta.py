"""元数据接口 — 数据字典。"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.exceptions import ErrorCode
from app.core.response import ApiResponse

router = APIRouter(prefix="/meta", tags=["数据字典"])


class ErrorCodeItem(BaseModel):
    """单个错误码条目 — 数据字典的一行。"""

    code: int = Field(..., description="数字错误码")
    name: str = Field(..., description="枚举名（英文，代码里用的标识）")
    description: str = Field(..., description="中文含义（给人看的说明）")


@router.get("/error-codes", response_model=ApiResponse[list[ErrorCodeItem]], summary="错误码数据字典")
async def list_error_codes() -> ApiResponse[list[ErrorCodeItem]]:
    """返回全量错误码对照表 { code, name, description }。

    枚举定义在 app/core/exceptions.py，描述和代码同源，
    改了错误码这里自动跟着变，不需要单独维护。
    """
    items = [ErrorCodeItem(code=int(member), name=member.name, description=member.description) for member in ErrorCode]
    return ApiResponse.ok(data=items)

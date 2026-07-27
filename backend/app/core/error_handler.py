"""全局异常处理器 — BusinessException → HTTP 200 + 标准格式。其他异常 → 原生 500。"""

import traceback

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import BusinessException
from app.core.logger import logger
from app.schemas.response import ApiResponse


async def business_exception_handler(request: Request, exc: BusinessException):
    logger.bind(
        path=request.url.path,
        code=int(exc.code),
    ).warning(f"[{int(exc.code)}] {exc.message}")
    result = ApiResponse.fail(code=int(exc.code), message=exc.message, details=exc.details)
    return JSONResponse(status_code=200, content=result.model_dump())


async def unhandled_exception_handler(request: Request, exc: Exception):
    """未捕获异常 → 保持原生 500，打印完整堆栈。"""
    logger.error(
        f"未捕获异常 [{request.method} {request.url.path}]: {exc}\n{traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

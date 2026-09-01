"""
全局异常处理器 — 把所有异常转成统一的 JSON 响应。

两种处理策略：
  BusinessException → HTTP 200 + { code, message, details }
    业务层错误（用户不存在、权限不足、参数不对）返回 200，
    前端统一判断 code === 0 是否成功，不区分 HTTP 状态码。

  未知 Exception → HTTP 500 + { detail: "Internal Server Error" }
    真正的程序崩溃，不暴露内部细节给前端，完整堆栈只打印到服务器日志。
"""

import traceback

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.core.exceptions import BusinessException, ErrorCode
from app.core.logger import logger
from app.core.response import ApiResponse


async def business_exception_handler(request: Request, exc: BusinessException):
    """BusinessException → HTTP 200。

    示例：
      raise BusinessException(ErrorCode.USER_NOT_FOUND, "用户不存在: 42")
      → 前端收到 { code: 12001, message: "用户不存在: 42", data: null }

    所有 API 函数里抛的 BusinessException 都会经过这里。
    """
    logger.bind(
        path=request.url.path,
        code=int(exc.code),
    ).warning(f"[{int(exc.code)}] {exc.message}")
    result = ApiResponse.fail(code=int(exc.code), message=exc.message)
    return JSONResponse(status_code=200, content=result.model_dump())


async def unhandled_exception_handler(request: Request, exc: Exception):
    """未知异常 → HTTP 500。

    这种情况说明代码有 bug（比如 NoneType 调用了方法）。
    生产环境不暴露 traceback 给前端，避免泄漏内部信息。
    """
    logger.error(
        f"未捕获异常 [{request.method} {request.url.path}]: {exc}\n{traceback.format_exc()}"
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


async def db_operational_error_handler(request: Request, exc: OperationalError):
    """数据库瞬时错误（死锁/锁等待超时/连接断开）→ HTTP 200 + 冲突码。

    MySQL InnoDB 并发写时最常见的 1213 死锁、1205 锁等待超时都属于 OperationalError，
    它们是瞬时冲突而非业务错误，提示前端重试即可，不该返回 500。
    """
    logger.error(f"数据库操作冲突 [{request.method} {request.url.path}]: {exc}")
    return JSONResponse(
        status_code=200,
        content=ApiResponse.fail(
            code=int(ErrorCode.CONFLICT),
            message="操作冲突，请稍后重试",
        ).model_dump(),
    )

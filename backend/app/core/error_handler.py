"""
全局异常处理器 — 把所有异常转成统一的 JSON 响应。

两种异常处理策略：

  #1 BusinessException → HTTP 200 + { code, message, details }
     前端判断: if (res.code === 0) { 成功 } else { ElMessage.error(res.message) }
     为什么返回 200？因为这不是 HTTP 层的错误，
     是业务层的错误（用户不存在、权限不足、参数不对）。

  #2 未知 Exception → HTTP 500 + { detail: "Internal Server Error" }
     真正的程序崩了，不暴露内部错误细节给前端。
     完整堆栈只打印到服务器日志（loguru → stderr + logs/app.log）。
"""

import traceback

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exceptions import BusinessException
from app.core.logger import logger
from app.schemas.response import ApiResponse


async def business_exception_handler(request: Request, exc: BusinessException):
    """#1 BusinessException → HTTP 200。

    示例：
      raise BusinessException(ErrorCode.USER_NOT_FOUND, "用户不存在: 42")
      → 前端收到 { code: 12001, message: "用户不存在: 42", data: null }

    所有 API 函数里抛的 BusinessException 都会经过这里。
    """
    logger.bind(
        path=request.url.path,
        code=int(exc.code),
    ).warning(f"[{int(exc.code)}] {exc.message}")
    result = ApiResponse.fail(code=int(exc.code), message=exc.message, details=exc.details)
    return JSONResponse(status_code=200, content=result.model_dump())


async def unhandled_exception_handler(request: Request, exc: Exception):
    """#2 未知异常 → HTTP 500。

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

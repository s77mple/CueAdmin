"""全局异常处理器 — 把所有异常转成统一的 JSON 响应。"""

import traceback

from fastapi import Request
from fastapi.exceptions import RequestValidationError
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
    return JSONResponse(
        status_code=200, content=result.model_dump()
    )  # pydantic实例转 dict 用 model_dump()，而不是 dict(result)，否则会丢失字段描述信息


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Pydantic 入参校验失败 → HTTP 200 + 业务错误码（前端统一读 code，不区分 422/500）。

    只取第一条错误：errors[0]。loc 的末位元素就是字段名，msg 直接用，
    不拼 Pydantic 的技术前缀（前端只需要一句能展示的中文）。
    """
    errors = exc.errors()
    detail = errors[0] if errors else {}
    msg = detail.get("msg", "参数校验失败")
    field = detail.get("loc", ["unknown"])[-1] if detail.get("loc") else "unknown"
    logger.bind(path=request.url.path).warning(f"参数校验失败: {field} — {msg}")
    return JSONResponse(
        status_code=200,
        content=ApiResponse.fail(
            code=int(ErrorCode.VALIDATION_ERROR),
            message=msg,
        ).model_dump(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    """未知异常 → HTTP 500。

    这种情况说明代码有 bug（比如 NoneType 调用了方法）。
    生产环境不暴露 traceback 给前端，避免泄漏内部信息。
    """
    logger.error(f"未捕获异常 [{request.method} {request.url.path}]: {exc}\n{traceback.format_exc()}")
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

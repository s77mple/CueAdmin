"""应用入口 — FastAPI 启动、中间件、异常处理。

所有异常（业务异常或程序崩溃）都被全局 handler 捕获，转成统一的 { code, message, data }，
前端不用区分 HTTP 状态码。
"""

import os
import sys
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.system.api.v1.router import v1_router
from app.core.logger import logger
from app.core.exceptions import BusinessException, ErrorCode
from app.core.error_handler import (
    business_exception_handler,
    unhandled_exception_handler,
    db_operational_error_handler,
)
from app.core.response import ApiResponse
from app.core.storage import close_redis, async_engine
from app.core.dependencies import get_redis


def _docs_base_url() -> str:
    """推断后端地址，用于启动时打印文档链接。"""
    host, port = "127.0.0.1", 8000
    argv = sys.argv
    for i, arg in enumerate(argv):
        if arg == "--host" and i + 1 < len(argv):
            host = argv[i + 1]
        elif arg == "--port" and i + 1 < len(argv):
            port = argv[i + 1]
    host = os.getenv("HOST", host)
    port = os.getenv("PORT", port)
    if host in ("0.0.0.0", "::"):
        host = "127.0.0.1"
    return f"http://{host}:{port}"


# 应用生命周期：启动时校验配置，关闭时释放连接池
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_secrets()
    base = _docs_base_url()
    logger.info("应用启动完成")
    logger.info(f"Swagger 文档: {base}/docs")
    logger.info(f"ReDoc 文档:   {base}/redoc")
    logger.info(f"OpenAPI JSON: {base}/openapi.json")
    logger.info(f"错误码字典:   {base}/api/v1/system/meta/error-codes")
    yield
    logger.info("正在关闭 Redis 连接池...")
    await close_redis()
    logger.info("正在关闭数据库连接池...")
    await async_engine.dispose()
    logger.info("应用已关闭")


# request_max_size=10MB：防止超大请求体耗尽内存
app = FastAPI(
    title=settings.app_name,
    docs_url="/docs",
    lifespan=lifespan,
    request_max_size=10 * 1024 * 1024,
)


# Pydantic 校验失败 → HTTP 200 + 业务错误码（前端统一读 code，不区分 422/500）
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    detail = errors[0] if errors else {}
    msg = detail.get('msg', '参数校验失败')  # 只给中文文案，不带 Pydantic 技术前缀
    field = detail.get('loc', ['unknown'])[-1] if detail.get('loc') else 'unknown'
    logger.bind(path=request.url.path).warning(f"参数校验失败: {field} — {msg}")
    return JSONResponse(
        status_code=200,
        content=ApiResponse.fail(
            code=int(ErrorCode.VALIDATION_ERROR),
            message=msg,
        ).model_dump(),
    )


# 注册异常处理器（具体类型必须在 Exception 前面）
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(OperationalError, db_operational_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# CORS：token 放 localStorage + header，不走 cookie，故 allow_credentials=False
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip 压缩大于 1KB 的 JSON 响应
app.add_middleware(GZipMiddleware, minimum_size=1000)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    logger.bind(
        method=request.method, path=request.url.path,
        status=response.status_code, elapsed=f"{elapsed:.3f}s",
    ).info(f"{request.method} {request.url.path} → {response.status_code} ({elapsed:.3f}s)")
    return response


# 健康检查 — 供负载均衡 / K8s 探针使用
@app.get("/health", tags=["系统"])
async def health_check():
    """检查数据库和 Redis 是否连通。全 OK 返 200，否则 503。"""
    db_ok = False
    redis_ok = False

    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.warning(f"健康检查：数据库不可用 — {e}")

    try:
        r = await get_redis()
        await r.ping()
        redis_ok = True
    except Exception as e:
        logger.warning(f"健康检查：Redis 不可用 — {e}")

    all_ok = db_ok and redis_ok
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "status": "ok" if all_ok else "degraded",
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "error",
        },
    )


# 注册所有 API 路由 — 统一前缀 /api/v1
app.include_router(v1_router, prefix="/api/v1")

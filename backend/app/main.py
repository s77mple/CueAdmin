import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.router import api_router
from app.core.logger import logger
from app.core.exceptions import BusinessException, ErrorCode
from app.core.error_handler import business_exception_handler, unhandled_exception_handler
from app.schemas.response import ApiResponse
from app.core.dependencies import close_redis
from app.core.database import async_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时校验 secret
    settings.validate_secrets()
    logger.info("应用启动完成")
    yield
    # 优雅关闭：释放连接池
    logger.info("正在关闭 Redis 连接池...")
    await close_redis()
    logger.info("正在关闭数据库连接池...")
    await async_engine.dispose()
    logger.info("应用已关闭")


app = FastAPI(title=settings.app_name, docs_url="/docs", lifespan=lifespan)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Pydantic 校验失败 → HTTP 200 + 标准格式，不裸奔 422。"""
    errors = exc.errors()
    detail = errors[0] if errors else {}
    msg = f"参数校验失败: {detail.get('loc', ['unknown'])[-1]} — {detail.get('msg', '')}"
    logger.bind(path=request.url.path).warning(msg)
    return JSONResponse(
        status_code=200,
        content=ApiResponse.fail(
            code=int(ErrorCode.VALIDATION_ERROR),
            message=msg,
        ).model_dump(),
    )


# 业务异常 → HTTP 200 + 标准格式
app.add_exception_handler(BusinessException, business_exception_handler)
# Pydantic 校验异常 → HTTP 200 + 标准格式（必须在 Exception 之前注册）
app.add_exception_handler(RequestValidationError, validation_exception_handler)
# 未捕获异常 → 原生 500 + 日志堆栈
app.add_exception_handler(Exception, unhandled_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


app.include_router(api_router, prefix="/api/v1")

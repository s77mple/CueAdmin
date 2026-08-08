"""
应用入口 — FastAPI 启动、中间件、异常处理。

一个请求从进入服务器到返回的完整路径：
  浏览器 → CORS 中间件 → 日志中间件 → 路由匹配 → 依赖注入(认证鉴权)
  → API 函数 → 响应 → 日志中间件 → 浏览器

所有异常（不管是业务异常还是程序崩溃）都会被全局 handler 捕获，
转成统一的 { code, message, data } 格式返回，前端不用区分 HTTP 状态码。
"""

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


# 1. 应用生命周期：启动时校验配置，关闭时释放数据库连接池和 Redis 连接池
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1a. 启动：检查 .env 里 jwt_secret 和 database_url 有没有配好
    settings.validate_secrets()
    logger.info("应用启动完成")
    yield
    # 1b. 关闭：先关 Redis，再关数据库（顺序不重要，都是独立资源）
    logger.info("正在关闭 Redis 连接池...")
    await close_redis()
    logger.info("正在关闭数据库连接池...")
    await async_engine.dispose()
    logger.info("应用已关闭")


# 2. 创建 FastAPI 应用实例 — 所有请求/响应/中间件都挂在这上面
app = FastAPI(title=settings.app_name, docs_url="/docs", lifespan=lifespan)


# 3. Pydantic 参数校验失败的处理
#    正常 FastAPI 返回 422，我们统一转成 HTTP 200 + 业务错误码
#    前端不用区分 422/500/200，统一读 response.data.code 就行
async def validation_exception_handler(request: Request, exc: RequestValidationError):
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


# 4. 注册三个异常处理器（注意顺序：BusinessException 和 RequestValidationError 必须在 Exception 前面）
app.add_exception_handler(BusinessException, business_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# 5. CORS 中间件 — 允许前端跨域请求
#    allow_credentials=False：因为我们前端 token 放 localStorage + header 里，不走 cookie 认证
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 6. 请求日志中间件 — 记录每个请求的 方法、路径、耗时、响应状态
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)  # 6a. 放行请求，让后面的路由处理器处理
    elapsed = time.time() - start
    # 6b. 请求处理完毕，记录日志
    logger.bind(
        method=request.method, path=request.url.path,
        status=response.status_code, elapsed=f"{elapsed:.3f}s",
    ).info(f"{request.method} {request.url.path} → {response.status_code} ({elapsed:.3f}s)")
    return response


# 7. 注册所有 API 路由 — 统一前缀 /api/v1
#    例如 GET /api/v1/users 会路由到 app/api/users.py 里的 list_users 函数
app.include_router(api_router, prefix="/api/v1")

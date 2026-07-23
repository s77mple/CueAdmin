import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.router import api_router
from app.core.logger import logger

app = FastAPI(title=settings.app_name, docs_url="/docs")

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

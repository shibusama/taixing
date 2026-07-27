"""
钛星 (taixing) — FastAPI 后端
"""
import sys
import os

# Ensure project root is importable for crawlers/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db, auto_migrate
from app.routers.api import router
from app.scheduler import start_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    init_db()
    auto_migrate()
    start_scheduler()
    yield
    # 关闭时
    shutdown_scheduler()


app = FastAPI(
    title="钛星 API",
    description="钛星科技新闻聚合平台后端",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure DB is initialized at import time (also called during lifespan)
init_db()

app.include_router(router)

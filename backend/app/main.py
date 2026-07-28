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
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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

# 静态文件服务（生产环境）
# 项目根目录（包含 index.html 等静态文件）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

@app.get("/")
async def serve_index():
    """服务首页"""
    return FileResponse(os.path.join(PROJECT_ROOT, "index.html"))

# 挂载静态文件目录（CSS, JS, data, 图片等）
app.mount("/css", StaticFiles(directory=os.path.join(PROJECT_ROOT, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(PROJECT_ROOT, "js")), name="js")
app.mount("/data", StaticFiles(directory=os.path.join(PROJECT_ROOT, "data")), name="data")
app.mount("/assets", StaticFiles(directory=os.path.join(PROJECT_ROOT, "assets")), name="assets")

# 服务其他 HTML 页面
@app.get("/{page}")
async def serve_page(page: str):
    """服务其他 HTML 页面"""
    if page.endswith(".html"):
        file_path = os.path.join(PROJECT_ROOT, page)
        if os.path.exists(file_path):
            return FileResponse(file_path)
    # 尝试添加 .html 后缀
    file_path = os.path.join(PROJECT_ROOT, f"{page}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "Page not found"}, 404

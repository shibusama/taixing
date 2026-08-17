"""
钛星 (taixing) — FastAPI 后端
"""
import sys
import os

# Ensure project root is importable for crawlers/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load .env config from project root (API keys, scheduler switch)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))
except Exception:
    pass

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from app.database import init_db
from app.routers.api import router
from app.scheduler import start_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    init_db()
    if os.environ.get("SCHEDULER_ENABLED", "true").lower() in ("1", "true", "yes"):
        start_scheduler()
    else:
        print("[scheduler] disabled by SCHEDULER_ENABLED=false")
    yield
    # 关闭时
    shutdown_scheduler()


# CORS 配置：从环境变量读取允许的源，默认仅允许本地开发地址
_cors_origins = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:5000,http://127.0.0.1:5000,http://localhost:3000"
)
ALLOWED_ORIGINS = [o.strip() for o in _cors_origins.split(",") if o.strip()]

app = FastAPI(
    title="钛星 API",
    description="钛星科技新闻聚合平台后端",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


app.include_router(router)

# 静态文件服务（生产环境）
# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
# HTML 页面目录
PAGES_DIR = os.path.join(PROJECT_ROOT, "pages")


@app.get("/")
async def serve_index():
    """服务首页"""
    return FileResponse(os.path.join(PAGES_DIR, "index.html"))


# 挂载静态文件目录（CSS, JS, data 等）
app.mount("/css", StaticFiles(directory=os.path.join(PROJECT_ROOT, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(PROJECT_ROOT, "js")), name="js")
app.mount("/data", StaticFiles(directory=os.path.join(PROJECT_ROOT, "data")), name="data")
app.mount("/components", StaticFiles(directory=os.path.join(PROJECT_ROOT, "components")), name="components")


# 服务其他 HTML 页面
@app.get("/{page}")
async def serve_page(page: str):
    """服务其他 HTML 页面"""
    if page.endswith(".html"):
        file_path = os.path.join(PAGES_DIR, page)
        if os.path.exists(file_path):
            return FileResponse(file_path)
    # 尝试添加 .html 后缀
    file_path = os.path.join(PAGES_DIR, f"{page}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Page not found")

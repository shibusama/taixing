"""
閽涙槦 (taixing) 鈥?FastAPI 鍚庣
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
from app.database import init_db
from app.routers.api import router
from app.scheduler import start_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 鍚姩鏃?    init_db()
    start_scheduler()
    yield
    # 鍏抽棴鏃?    shutdown_scheduler()


app = FastAPI(
    title="閽涙槦 API",
    description="閽涙槦绉戞妧鏂伴椈鑱氬悎骞冲彴鍚庣",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)

# 静态文件服务（生产环境）
# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
# HTML 椤甸潰鐩綍
PAGES_DIR = os.path.join(PROJECT_ROOT, "pages")

@app.get("/")
async def serve_index():
    """鏈嶅姟棣栭〉"""
    return FileResponse(os.path.join(PAGES_DIR, "index.html"))

# 鎸傝浇闈欐€佹枃浠剁洰褰曪紙CSS, JS, data 绛夛級
app.mount("/css", StaticFiles(directory=os.path.join(PROJECT_ROOT, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(PROJECT_ROOT, "js")), name="js")
app.mount("/data", StaticFiles(directory=os.path.join(PROJECT_ROOT, "data")), name="data")
app.mount("/components", StaticFiles(directory=os.path.join(PROJECT_ROOT, "components")), name="components")

# 鏈嶅姟鍏朵粬 HTML 椤甸潰
@app.get("/{page}")
async def serve_page(page: str):
    """鏈嶅姟鍏朵粬 HTML 椤甸潰"""
    if page.endswith(".html"):
        file_path = os.path.join(PAGES_DIR, page)
        if os.path.exists(file_path):
            return FileResponse(file_path)
    # 灏濊瘯娣诲姞 .html 鍚庣紑
    file_path = os.path.join(PAGES_DIR, f"{page}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "Page not found"}, 404

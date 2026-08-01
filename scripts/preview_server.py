#!/usr/bin/env python3
"""
Coze 预览服务器
同时服务静态文件和 FastAPI API
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 导入后端 API 应用
from backend.app.main import app as backend_app

# 使用后端应用作为基础
app = backend_app

# 添加 CORS 中间件（如果还没有）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件服务（放在最后，这样 API 路由优先匹配）
# HTML 文件在 pages/ 目录，其他静态文件（css/js/data）在根目录
app.mount("/css", StaticFiles(directory=str(PROJECT_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(PROJECT_DIR / "js")), name="js")
app.mount("/data", StaticFiles(directory=str(PROJECT_DIR / "data")), name="data")
app.mount("/assets", StaticFiles(directory=str(PROJECT_DIR / "assets")), name="assets")

app.mount("/components", StaticFiles(directory=str(PROJECT_DIR / "components")), name="components")
app.mount("/", StaticFiles(directory=str(PROJECT_DIR / "pages"), html=True), name="static")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[preview-server] 启动预览服务器，监听 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

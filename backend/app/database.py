"""
兼容层 — 从 app.db 子模块 re-export 所有公开函数
"""
from app.db import *  # noqa: F401, F403

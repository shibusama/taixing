# -*- coding: utf-8 -*-
"""
本地 SQLite 双模式数据库层（backend/app/db/local/）
- schema.py        ：28 张表建表定义（schema.ts + ai_extract_logs.sql + 代码推断）
- local_client.py  ：supabase 兼容链式 API 的 SQLite 适配层
- seed.py          ：预留种子入口（骨架）
"""
from .local_client import (
    LocalClient,
    LocalQuery,
    LocalResult,
    create_client,
    get_client,
    get_db_path,
    init_db,
)
from . import schema
from .seed import seed_from_json

__all__ = [
    "LocalClient",
    "LocalQuery",
    "LocalResult",
    "create_client",
    "get_client",
    "get_db_path",
    "init_db",
    "schema",
    "seed_from_json",
]

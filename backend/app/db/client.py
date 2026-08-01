# -*- coding: utf-8 -*-
"""
Supabase / 本地 SQLite 双模式数据库客户端初始化

- 配置了 COZE_SUPABASE_URL 且拿到 key（COZE_SUPABASE_SERVICE_ROLE_KEY 或 COZE_SUPABASE_ANON_KEY）：
  走 Supabase（supabase-py 链式 API，行为不变）
- 未配置 Supabase 环境变量：自动降级为本地 SQLite（backend/app/db/local/local_client.py，
  零第三方依赖），数据库文件默认位于项目根 .local/taixing.db（可用 TAIXING_DB_PATH 覆盖）

现有业务代码无需任何改动：两种模式下 get_supabase() 返回的对象均支持
table/select/eq/or_/ilike/in_/order/limit/range/insert/update/delete/execute 链式调用，
execute() 结果带 .data（list）与 .count（int|None）。
"""
import os
from typing import Optional

_supabase = None
_env_loaded = False
_MODE = "local"  # "supabase" | "local"


def _load_env() -> None:
    """通过 workload identity 加载 Supabase 环境变量（如尚未设置）"""
    global _env_loaded
    if _env_loaded or (os.environ.get("COZE_SUPABASE_URL") and os.environ.get("COZE_SUPABASE_ANON_KEY")):
        return
    try:
        from coze_workload_identity import Client as WorkloadClient
        client = WorkloadClient()
        env_vars = client.get_project_env_vars()
        client.close()
        for v in env_vars:
            if not os.environ.get(v.key):
                os.environ[v.key] = v.value
        _env_loaded = True
    except Exception:
        pass


def get_supabase():
    """获取数据库客户端：有 Supabase 环境变量走 Supabase，否则返回本地 SQLite 客户端"""
    global _supabase, _MODE
    if _supabase is None:
        _load_env()
        supabase_url = os.environ.get("COZE_SUPABASE_URL")
        supabase_key = os.environ.get("COZE_SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("COZE_SUPABASE_ANON_KEY")

        if supabase_url and supabase_key:
            from supabase import create_client
            _supabase = create_client(supabase_url, supabase_key)
            _MODE = "supabase"
        else:
            from app.db.local.local_client import create_client as _create_local_client
            _supabase = _create_local_client(url=supabase_url, key=supabase_key)
            _MODE = "local"
    return _supabase


def get_db_mode() -> str:
    """返回当前数据库模式：'supabase' / 'local'"""
    get_supabase()
    return _MODE


def init_db():
    """初始化数据库：Supabase 模式仅验证连接；本地模式自动建全部表（幂等 CREATE TABLE IF NOT EXISTS）"""
    sb = get_supabase()
    if _MODE == "local":
        sb.init_db()
        print(f"数据库初始化成功（本地 SQLite: {sb.db_path}）")
    else:
        print("数据库连接成功（Supabase）")

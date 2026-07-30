"""
Supabase 客户端初始化
"""
import os
from typing import Optional
from supabase import create_client, Client

_supabase: Optional[Client] = None
_env_loaded = False


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


def get_supabase() -> Client:
    """获取 Supabase 客户端"""
    global _supabase
    if _supabase is None:
        _load_env()
        supabase_url = os.environ.get("COZE_SUPABASE_URL")
        supabase_key = os.environ.get("COZE_SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("COZE_SUPABASE_ANON_KEY")

        if not supabase_url or not supabase_key:
            raise RuntimeError("Supabase 环境变量未配置：需要 COZE_SUPABASE_URL 和 COZE_SUPABASE_ANON_KEY")

        _supabase = create_client(supabase_url, supabase_key)
    return _supabase


def init_db():
    """初始化数据库"""
    try:
        sb = get_supabase()
        print("数据库连接成功（Supabase）")
    except Exception as e:
        print(f"数据库连接失败：{e}")
        raise

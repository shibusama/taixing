"""
板块操作 — board_status / board_meta 表
"""
from datetime import datetime
from typing import Optional, List, Dict
from app.db.client import get_supabase


def get_board_status(board_id: str) -> Optional[Dict]:
    sb = get_supabase()
    result = sb.table("board_status").select("*").eq("board_id", board_id).execute()
    return result.data[0] if result.data else None


def get_all_board_status() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("board_status").select("*").execute()
    return result.data


def update_board_status(board_id: str, total_new: int = 0, total_sources: int = 0, error_sources: int = 0, msg: str = ""):
    """更新板块状态（由 run_crawler 调用）"""
    sb = get_supabase()
    now = datetime.now().isoformat()

    existing = get_board_status(board_id)
    if existing:
        new_count = int(existing.get("new_items_count") or 0) + total_new
        sb.table("board_status").update({
            "new_items_count": str(new_count),
            "total_sources": str(total_sources),
            "error_sources": str(error_sources),
            "last_crawled_at": now,
            "last_message": msg,
        }).eq("board_id", board_id).execute()
    else:
        sb.table("board_status").insert({
            "board_id": board_id,
            "new_items_count": str(total_new),
            "total_sources": str(total_sources),
            "error_sources": str(error_sources),
            "last_crawled_at": now,
            "last_message": msg,
        }).execute()


def get_board(board_id: str) -> Optional[Dict]:
    """兼容接口 — 同 get_board_status"""
    sb = get_supabase()
    result = sb.table("board_status").select("*").eq("board_id", board_id).execute()
    return result.data[0] if result.data else None


def list_boards() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("board_status").select("*").execute()
    return result.data


def get_board_meta(board_id: str) -> Optional[Dict]:
    """获取板块元信息"""
    sb = get_supabase()
    result = sb.table("board_meta").select("*").eq("board_id", board_id).execute()
    return result.data[0] if result.data else None

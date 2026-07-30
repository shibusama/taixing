"""
管理功能 — crawl_logs / latest_news
"""
from datetime import datetime
from typing import List, Dict, Optional
from app.db.client import get_supabase


# ============ crawl_logs ============

def log_crawl(board_id: str, status: str, message: str = "", items_count: int = 0):
    sb = get_supabase()
    now = datetime.now().isoformat()
    sb.table("crawl_logs").insert({
        "board_id": board_id,
        "source_name": "scheduler",
        "status": status,
        "error_message": message if status == "failed" else None,
        "items_count": items_count,
        "started_at": now,
        "finished_at": now,
        "created_at": now,
    }).execute()


def get_crawl_logs(board_id: str = None, limit: int = 20) -> List[Dict]:
    sb = get_supabase()
    query = sb.table("crawl_logs").select("*")
    if board_id:
        query = query.eq("board_id", board_id)
    result = query.order("created_at", desc=True).limit(limit).execute()
    return result.data


def get_global_last_updated() -> str:
    """返回所有板块中最新数据更新时间"""
    sb = get_supabase()
    result = sb.table("crawl_logs").select("created_at").order("created_at", desc=True).limit(1).execute()
    if result.data:
        return result.data[0].get("created_at", "")
    return ""


# ============ latest_news ============

def get_latest_news(limit: int = 10) -> List[Dict]:
    """获取最新要闻列表（仅 active，按 sort_order + publish_date 排序）"""
    sb = get_supabase()
    result = (
        sb.table("latest_news")
        .select("*")
        .eq("is_active", True)
        .order("sort_order", desc=False)
        .order("publish_date", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data


def get_all_latest_news() -> List[Dict]:
    """获取全部最新要闻（含 inactive，管理后台用）"""
    sb = get_supabase()
    result = (
        sb.table("latest_news")
        .select("*")
        .order("sort_order", desc=False)
        .order("publish_date", desc=True)
        .execute()
    )
    return result.data


def create_latest_news(item: Dict) -> Dict:
    """新增一条最新要闻"""
    sb = get_supabase()
    result = sb.table("latest_news").insert(item).execute()
    return result.data[0] if result.data else {}


def update_latest_news(news_id: int, updates: Dict) -> Dict:
    """更新一条最新要闻"""
    sb = get_supabase()
    updates["updated_at"] = datetime.now().isoformat()
    result = sb.table("latest_news").update(updates).eq("id", news_id).execute()
    return result.data[0] if result.data else {}


def delete_latest_news(news_id: int) -> bool:
    """删除一条最新要闻"""
    sb = get_supabase()
    sb.table("latest_news").delete().eq("id", news_id).execute()
    return True

"""
钛星科技新闻站 - 数据库模块
使用 Supabase (Coze 内置数据库)

列名严格匹配生产环境 schema（从 SQLite 迁移而来）：
  - board_status: board_id, last_crawled_at, new_items_count, total_sources, error_sources, last_message, rocket_intro
  - raw_articles: board_id, source, title, url, summary, date, raw_json, dedup_key, is_new, created_at
  - crawl_logs: board_id, status, source_name, items_count, error_message, started_at, finished_at, created_at
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from supabase import create_client, Client

_supabase: Optional[Client] = None


def get_supabase() -> Client:
    """获取 Supabase 客户端"""
    global _supabase
    if _supabase is None:
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


# ============ board_status ============

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


# ============ boards 兼容 ============

def get_board(board_id: str) -> Optional[Dict]:
    sb = get_supabase()
    result = sb.table("board_status").select("*").eq("board_id", board_id).execute()
    return result.data[0] if result.data else None


def list_boards() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("board_status").select("*").execute()
    return result.data


# ============ raw_articles ============

def get_raw_articles(board_id: str = None, limit: int = 50) -> List[Dict]:
    sb = get_supabase()
    query = sb.table("raw_articles").select("*")
    if board_id:
        query = query.eq("board_id", board_id)
    result = query.order("created_at", desc=True).limit(limit).execute()
    return result.data


def insert_raw_article(article: Dict) -> int:
    sb = get_supabase()
    result = sb.table("raw_articles").insert(article).execute()
    if result.data:
        return result.data[0].get("id", 0)
    return 0


def upsert_article(board_id: str, source: str, title: str, url: str, summary: str = "", date: str = "", raw_json: str = "") -> bool:
    """插入或更新文章（去重：按 board_id + url）。返回 True 表示新增。"""
    sb = get_supabase()
    existing = sb.table("raw_articles").select("id").eq("board_id", board_id).eq("url", url).limit(1).execute()
    if existing.data:
        return False

    dedup_key = f"{board_id}:{url}"
    sb.table("raw_articles").insert({
        "board_id": board_id,
        "source": source,
        "title": title,
        "url": url,
        "summary": summary,
        "date": date or None,
        "raw_json": raw_json,
        "dedup_key": dedup_key,
        "is_new": "true",
        "created_at": datetime.now().isoformat(),
    }).execute()
    return True


def update_article(article_id: int, **kwargs):
    sb = get_supabase()
    sb.table("raw_articles").update(kwargs).eq("id", article_id).execute()


def delete_article(article_id: int):
    sb = get_supabase()
    sb.table("raw_articles").delete().eq("id", article_id).execute()


def get_recent_articles(board_id: str = None, limit: int = 10) -> List[Dict]:
    sb = get_supabase()
    query = sb.table("raw_articles").select("*")
    if board_id:
        query = query.eq("board_id", board_id)
    result = query.order("created_at", desc=True).limit(limit).execute()
    return result.data


def get_articles_stats(board_id: str = None) -> Dict:
    sb = get_supabase()
    query = sb.table("raw_articles").select("id")
    if board_id:
        query = query.eq("board_id", board_id)
    result = query.execute()
    return {"total": len(result.data)}


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


# ============ 全局更新时间 ============

def get_global_last_updated() -> str:
    sb = get_supabase()
    result = sb.table("crawl_logs").select("created_at").order("created_at", desc=True).limit(1).execute()
    if result.data:
        return result.data[0].get("created_at", "")
    return ""


# ============ 爬虫分类工具 ============

def _classify_crawled_item(item: dict) -> tuple:
    """从爬虫返回的 dict 中提取标准化字段。返回 (title, url, summary, date, raw_json)"""
    title = str(item.get("title", "") or "").strip()
    url = str(item.get("url", "") or item.get("link", "") or "").strip()
    summary = str(item.get("summary", "") or item.get("description", "") or item.get("content", "") or "").strip()
    date = str(item.get("date", "") or item.get("published_at", "") or item.get("pubDate", "") or "").strip()
    raw_json = json.dumps(item, ensure_ascii=False) if item else ""
    return title, url, summary, date, raw_json


# ============ 火箭板块 ============

def get_rocket_companies() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("rocket_companies").select("*").execute()
    return result.data


def get_rocket_timeline() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("rocket_timeline").select("*").execute()
    return result.data


def get_rocket_intro() -> Optional[Dict]:
    sb = get_supabase()
    result = sb.table("board_status").select("rocket_intro").eq("board_id", "rocket").execute()
    if result.data:
        return {"intro": result.data[0].get("rocket_intro", "")}
    return None


def set_rocket_intro(intro: str):
    sb = get_supabase()
    sb.table("board_status").update({"rocket_intro": intro}).eq("board_id", "rocket").execute()


def sync_launch_api_to_timeline():
    return 0


def sync_rocket_companies():
    return 0


# ============ 登月板块 ============

def get_moon_highlights() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("moon_highlights").select("*").execute()
    return result.data


def get_moon_comparison() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("moon_comparison").select("*").execute()
    return result.data


# ============ 半导体板块 ============

def get_semiconductor_highlights() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("semiconductor_highlights").select("*").execute()
    return result.data


def get_semiconductor_tab_highlights() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("semiconductor_tab_highlights").select("*").execute()
    return result.data


def get_semiconductor_tab_progress() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("semiconductor_tab_progress").select("*").execute()
    return result.data


# ============ 中国科技 AI ============

def get_china_tech_highlights() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("china_tech_highlights").select("*").execute()
    return result.data


def get_china_tech_llm() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("china_tech_llm").select("*").execute()
    return result.data


# ============ 大工程 ============

def get_mega_projects() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("mega_projects").select("*").execute()
    return result.data


def get_mega_project_highlights() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("mega_project_highlights").select("*").execute()
    return result.data


def get_mega_project_milestones() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("mega_project_milestones").select("*").execute()
    return result.data


# ============ 核聚变 ============

def get_fusion_highlights() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("fusion_highlights").select("*").execute()
    return result.data


def get_fusion_timeline() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("fusion_timeline").select("*").execute()
    return result.data


# ============ 科技资本 ============

def get_finance_grids() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("finance_grids").select("*").execute()
    return result.data


def get_finance_highlights() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("finance_highlights").select("*").execute()
    return result.data


def get_finance_sections() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("finance_sections").select("*").execute()
    return result.data


# ============ 同步 / 重同步 ============

def re_sync_all_from_json():
    pass


def re_sync_board_from_json(board_id: str):
    pass


# ============ 兼容旧代码 ============

def get_cursor():
    return None


def _list(data):
    return data if isinstance(data, list) else []

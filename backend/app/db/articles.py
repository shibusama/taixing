"""
文章操作 — raw_articles 表
"""
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
from app.db.client import get_supabase


def upsert_news_article(article: Dict) -> bool:
    """
    插入或更新新闻（去重：按 news_id，即 URL 哈希）。
    article 需包含: news_id, source_name, source_url, title 等字段。
    返回 True 表示新增，False 表示已存在。
    """
    sb = get_supabase()
    news_id = article.get("news_id", "")
    if not news_id:
        return False

    # 检查是否已存在
    existing = sb.table("raw_articles").select("news_id").eq("news_id", news_id).limit(1).execute()
    if existing.data:
        return False

    # 插入新文章（过滤掉以 _ 开头的临时字段）
    clean_article = {k: v for k, v in article.items() if not k.startswith('_')}
    sb.table("raw_articles").insert(clean_article).execute()
    return True


def upsert_article(board_id: str, source: str, title: str, url: str, summary: str, date: str, raw_json: str) -> bool:
    """按 dedup_key（URL 的 MD5）去重写入 raw_articles。返回 True 表示新增"""
    sb = get_supabase()
    dedup_key = hashlib.md5(url.encode("utf-8")).hexdigest()

    existing = sb.table("raw_articles").select("id").eq("dedup_key", dedup_key).limit(1).execute()
    if existing.data:
        return False

    sb.table("raw_articles").insert({
        "board_id": board_id,
        "source": source,
        "title": title,
        "url": url,
        "summary": summary,
        "date": date,
        "raw_json": raw_json,
        "dedup_key": dedup_key,
        "created_at": datetime.now().isoformat(),
    }).execute()
    return True


def get_raw_articles(category: str = None, status: str = None, limit: int = 50, offset: int = 0) -> List[Dict]:
    """获取新闻列表（用于管理后台）"""
    sb = get_supabase()
    query = sb.table("raw_articles").select("*").order("crawl_time", desc=True)
    if category:
        query = query.eq("category", category)
    if status:
        query = query.eq("status", status)
    result = query.range(offset, offset + limit - 1).execute()
    return result.data


def get_raw_article_stats(category: str = None) -> Dict:
    """获取新闻统计"""
    sb = get_supabase()
    try:
        query = sb.table("raw_articles").select("news_id")
        if category:
            query = query.eq("category", category)
        result = query.execute()
        total = len(result.data) if result.data else 0

        # 统计各状态数量
        pending_query = sb.table("raw_articles").select("news_id").eq("status", "pending")
        online_query = sb.table("raw_articles").select("news_id").eq("status", "online")
        if category:
            pending_query = pending_query.eq("category", category)
            online_query = online_query.eq("category", category)
        pending_result = pending_query.execute()
        online_result = online_query.execute()

        return {
            "total": total,
            "pending": len(pending_result.data) if pending_result.data else 0,
            "online": len(online_result.data) if online_result.data else 0,
        }
    except Exception as e:
        print(f"[stats error] {e}")
        return {"total": 0, "pending": 0, "online": 0}


def update_article_status(news_id: str, status: str) -> bool:
    """更新文章状态（pending/online/block）"""
    sb = get_supabase()
    result = sb.table("raw_articles").update({"status": status}).eq("news_id", news_id).execute()
    return len(result.data) > 0 if result.data else False


def update_article(news_id: str, **kwargs) -> bool:
    """更新文章字段"""
    sb = get_supabase()
    result = sb.table("raw_articles").update(kwargs).eq("news_id", news_id).execute()
    return len(result.data) > 0 if result.data else False


def delete_raw_article(news_id: str) -> bool:
    """删除新闻"""
    sb = get_supabase()
    sb.table("raw_articles").delete().eq("news_id", news_id).execute()
    return True


def _classify_crawled_item(item: dict) -> tuple:
    """从爬虫返回的 dict 中提取标准化字段。返回 (title, url, summary, date, raw_json)"""
    title = str(item.get("title", "") or "").strip()
    url = str(item.get("url", "") or item.get("link", "") or "").strip()
    summary = str(item.get("summary", "") or item.get("description", "") or item.get("content", "") or "").strip()
    date = str(item.get("date", "") or item.get("published_at", "") or item.get("pubDate", "") or "").strip()
    raw_json = json.dumps(item, ensure_ascii=False) if item else ""
    return title, url, summary, date, raw_json


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

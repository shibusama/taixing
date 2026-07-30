from fastapi import APIRouter, HTTPException
from app.database import get_board, get_board_full, list_boards, log_crawl
from app.services.crawler_service import run_crawler
from crawlers.crawler_registry import CRAWLER_MODULES, BOARD_IDS

router = APIRouter(prefix="/api")

@router.post("/sync/rocket")
def api_sync_rocket_timeline():
    from app.database import sync_launch_api_to_timeline
    from app.database import sync_rocket_companies
    timeline_count = sync_launch_api_to_timeline()
    companies_count = sync_rocket_companies()
    return {"status": "ok", "timeline_synced": timeline_count, "companies_synced": companies_count}

@router.post("/sync/rocket-companies")
def api_sync_rocket_companies_only():
    from app.database import sync_rocket_companies
    count = sync_rocket_companies()
    return {"status": "ok", "companies_synced": count}

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/boards")
def api_list_boards():
    return list_boards()

@router.get("/boards/{board_id}")
def api_get_board(board_id: str):
    data = get_board(board_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Board {board_id!r} not found")
    return data

@router.get("/boards/{board_id}/full")
def api_get_board_full(board_id: str):
    data = get_board_full(board_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Board {board_id!r} not found")
    return data

@router.post("/crawl/{board_id}")
def api_crawl_board(board_id: str):
    try:
        result = run_crawler(board_id)
        log_crawl(board_id, "success", result.get("message", "OK"))
        return {"board_id": board_id, "status": "success", "detail": result}
    except Exception as e:
        log_crawl(board_id, "failed", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/crawl")
def api_crawl_all():
    results = {}
    for bid in CRAWLER_MODULES:
        try:
            results[bid] = run_crawler(bid)
        except Exception as e:
            results[bid] = {"error": str(e)}
    return {"status": "done", "results": results}

@router.get("/articles/{board_id}")
def api_get_articles(board_id: str, limit: int = 20):
    from app.database import get_recent_articles, get_articles_stats
    articles = get_recent_articles(board_id, limit)
    stats = get_articles_stats(board_id)
    return {"board_id": board_id, "stats": stats, "articles": articles}

@router.get("/last-updated")
def api_last_updated():
    from app.database import get_global_last_updated
    return {"last_updated": get_global_last_updated()}

@router.get("/rocket-intro")
def api_get_rocket_intro():
    from app.database import get_rocket_intro
    return {"intro": get_rocket_intro()}

@router.get("/rocket-timeline")
def api_get_rocket_timeline():
    from app.database import get_launch_timeline
    return {"timeline": get_launch_timeline(limit=100)}

@router.get("/status/{board_id}")
def api_get_board_status(board_id: str):
    from app.database import get_board_status
    s = get_board_status(board_id)
    if s is None:
        return {"board_id": board_id, "status": "never_crawled"}
    return {"board_id": board_id, **s}

# ---- admin articles ----

@router.get("/admin/articles")
def api_get_raw_articles(category: str = None, status: str = None, limit: int = 50, offset: int = 0):
    from app.database import get_raw_articles, get_raw_article_stats
    try:
        articles = get_raw_articles(category, status, limit, offset)
        stats = get_raw_article_stats(category)
        return {"stats": stats, "articles": articles}
    except Exception as e:
        print(f"[admin articles error] {e}")
        return {"stats": {"total": 0, "pending": 0, "online": 0}, "articles": []}

@router.post("/admin/articles/{news_id}/status")
def api_update_article_status(news_id: str, status: str):
    from app.database import update_article_status
    success = update_article_status(news_id, status)
    if success:
        return {"status": "ok", "message": "status updated"}
    raise HTTPException(status_code=500, detail="update failed")

@router.put("/admin/articles/{news_id}")
def api_update_article(news_id: str, content: dict):
    from app.database import update_article
    success = update_article(news_id, **content)
    if success:
        return {"status": "ok", "message": "updated"}
    raise HTTPException(status_code=500, detail="update failed")

@router.delete("/admin/articles/{news_id}")
def api_delete_article(news_id: str):
    from app.database import delete_raw_article
    delete_raw_article(news_id)
    return {"status": "ok", "message": "deleted"}

# ---- async crawl logs ----

_crawl_logs = {}

@router.post("/crawl/{board_id}/start")
def api_crawl_board_async(board_id: str):
    import threading
    from app.database import log_crawl
    from datetime import datetime

    _crawl_logs[board_id] = {
        "status": "running",
        "lines": [],
        "started_at": datetime.now().isoformat()
    }

    def _run():
        try:
            _crawl_logs[board_id]["lines"].append(f"[{board_id}] starting...")
            result = run_crawler(board_id)
            _crawl_logs[board_id]["lines"].append(f"[{board_id}] done: {result.get("message", "OK")}")
            _crawl_logs[board_id]["status"] = "success"
            log_crawl(board_id, "success", result.get("message", "OK"))
        except Exception as e:
            _crawl_logs[board_id]["lines"].append(f"[{board_id}] error: {e}")
            _crawl_logs[board_id]["status"] = "failed"
            log_crawl(board_id, "failed", str(e))

    threading.Thread(target=_run, daemon=True).start()
    return {"board_id": board_id, "status": "started"}

@router.get("/crawl/{board_id}/logs")
def api_get_crawl_logs(board_id: str):
    if board_id not in _crawl_logs:
        return {"status": "idle", "lines": []}
    return _crawl_logs[board_id]

# ---- AI extract ----

@router.post("/ai/extract")
def api_ai_extract(category: str = None, limit: int = 10):
    try:
        from app.ai_extractor import process_pending_articles
        result = process_pending_articles(category=category, limit=limit, auto_insert=True)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e), "total": 0, "results": []}

@router.get("/ai/stats")
def api_ai_stats():
    from app.database import get_supabase
    sb = get_supabase()
    pending_count = 0
    board_pending = {}
    try:
        pending_all = sb.table("raw_articles").select("news_id", count="exact").eq("status", "pending").execute()
        pending_count = pending_all.count if hasattr(pending_all, "count") and pending_all.count else len(pending_all.data)
        boards = sb.table("raw_articles").select("category").eq("status", "pending").execute()
        for row in boards.data or []:
            c = row.get("category", "unknown")
            board_pending[c] = board_pending.get(c, 0) + 1
    except Exception:
        pass
    news_total = 0
    try:
        news_count = sb.table("latest_news").select("id", count="exact").execute()
        news_total = news_count.count if hasattr(news_count, "count") and news_count.count else len(news_count.data)
    except Exception:
        pass
    return {
        "pending_articles": pending_count,
        "pending_by_board": board_pending,
        "latest_news_total": news_total,
        "status": "ok",
    }

# ---- latest news ----

@router.get("/latest-news")
def api_get_latest_news(limit: int = 10):
    from app.database import get_latest_news
    return {"items": get_latest_news(limit)}

@router.get("/admin/latest-news")
def api_get_all_latest_news():
    from app.database import get_all_latest_news
    return {"items": get_all_latest_news()}

@router.post("/admin/latest-news")
def api_create_latest_news(item: dict):
    from app.database import create_latest_news
    data = create_latest_news(item)
    return {"status": "ok", "data": data}

@router.put("/admin/latest-news/{news_id}")
def api_update_latest_news(news_id: int, updates: dict):
    from app.database import update_latest_news
    data = update_latest_news(news_id, updates)
    if data:
        return {"status": "ok", "data": data}
    raise HTTPException(status_code=404, detail="not found")

@router.delete("/admin/latest-news/{news_id}")
def api_delete_latest_news(news_id: int):
    from app.database import delete_latest_news
    delete_latest_news(news_id)
    return {"status": "ok"}


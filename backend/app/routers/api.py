import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from app.database import get_board, get_board_full, list_boards, log_crawl
from app.services.crawler_service import run_crawler
from crawlers.crawler_registry import CRAWLER_MODULES, BOARD_IDS

# 线程池：将同步爬虫放到独立线程执行，避免阻塞 async event loop
_crawl_executor = ThreadPoolExecutor(max_workers=4)

router = APIRouter(prefix="/api")

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
async def api_crawl_board(board_id: str):
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(_crawl_executor, run_crawler, board_id)
        log_crawl(board_id, "success", result.get("message", "OK"))
        return {"board_id": board_id, "status": "success", "detail": result}
    except Exception as e:
        log_crawl(board_id, "failed", str(e))
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/crawl")
async def api_crawl_all():
    loop = asyncio.get_event_loop()
    results = {}
    for bid in CRAWLER_MODULES:
        try:
            results[bid] = await loop.run_in_executor(_crawl_executor, run_crawler, bid)
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
    raw = get_rocket_intro() or {}
    if isinstance(raw, dict):
        intro = raw.get("intro", "")
    else:
        intro = raw
    return {"intro": intro if isinstance(intro, str) else ""}

@router.get("/rocket-next-intro")
def api_get_rocket_next_intro():
    from app.database import get_rocket_next_intro
    return {"intro": get_rocket_next_intro() or ""}

@router.get("/rocket-last-review")
def api_get_rocket_last_review():
    from app.database import get_rocket_last_review
    return {"review": get_rocket_last_review() or ""}

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

# ---- admin v3：仪表盘 / 文章审核 / 历史 / 数据同步 ----

@router.get("/admin/stats")
def api_admin_stats():
    """仪表盘总览：文章统计 + 版块状态 + 最近爬取/AI 记录"""
    from app.database import get_admin_stats
    try:
        return get_admin_stats()
    except Exception as e:
        print(f"[admin stats error] {e}")
        return {
            "articles": {"total": 0, "pending": 0, "online": 0, "block": 0},
            "boards": [],
            "recent_crawl_logs": [],
            "recent_ai_logs": [],
            "latest_news_total": 0,
        }


@router.get("/admin/boards/status")
def api_admin_boards_status():
    """版块状态面板"""
    from app.database import get_all_board_status
    try:
        return {"items": get_all_board_status()}
    except Exception as e:
        print(f"[admin boards status error] {e}")
        return {"items": []}


@router.get("/admin/crawl-logs")
def api_admin_crawl_logs(board_id: str = None, limit: int = 20):
    """历史爬虫日志"""
    from app.database import get_crawl_logs
    limit = min(max(1, limit), 200)
    try:
        return {"items": get_crawl_logs(board_id, limit)}
    except Exception as e:
        print(f"[admin crawl-logs error] {e}")
        return {"items": []}


@router.get("/admin/articles")
def api_get_raw_articles(
    category: str = None,
    status: str = None,
    keyword: str = None,
    sort_by: str = "crawl_time",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
):
    """文章列表：分页 + keyword 搜索 + 分类/状态筛选 + 排序。返回 {stats, items, total, page, page_size}"""
    from app.database import get_raw_articles, count_raw_articles, get_raw_article_stats
    if sort_by not in ("crawl_time", "publish_time", "source_name", "hot_score"):
        sort_by = "crawl_time"
    if sort_order not in ("asc", "desc"):
        sort_order = "desc"
    page = max(1, page)
    page_size = min(max(1, page_size), 200)
    try:
        items = get_raw_articles(category, status, keyword, sort_by=sort_by, sort_order=sort_order, page=page, page_size=page_size)
        stats = get_raw_article_stats(category, keyword)
        total = count_raw_articles(category, status, keyword)
        return {"stats": stats, "items": items, "total": total, "page": page, "page_size": page_size}
    except Exception as e:
        print(f"[admin articles error] {e}")
        return {"stats": {"total": 0, "pending": 0, "online": 0, "block": 0}, "items": [], "total": 0, "page": page, "page_size": page_size}


@router.get("/admin/articles/{news_id}")
def api_get_raw_article(news_id: str):
    """单条文章详情"""
    from app.database import get_raw_article
    item = get_raw_article(news_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Article {news_id!r} not found")
    return {"item": item}


@router.post("/admin/articles/batch-status")
def api_batch_update_article_status(body: dict):
    """批量审核：body = {"news_ids": [...], "status": "online"|"block"|"pending"}"""
    from app.database import batch_update_article_status
    news_ids = body.get("news_ids") or []
    status = body.get("status")
    if not isinstance(news_ids, list) or not news_ids:
        raise HTTPException(status_code=400, detail="news_ids 不能为空")
    if status not in ("online", "block", "pending"):
        raise HTTPException(status_code=400, detail="status 必须是 online/block/pending")
    try:
        updated = batch_update_article_status(news_ids, status)
        return {"status": "ok", "updated": updated, "total": len(news_ids)}
    except Exception as e:
        print(f"[admin batch-status error] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/ai/logs")
def api_admin_ai_logs(limit: int = 20):
    """AI 提取历史记录（ai_extract_logs）"""
    from app.database import get_ai_extract_logs
    limit = min(max(1, limit), 200)
    try:
        return {"items": get_ai_extract_logs(limit)}
    except Exception as e:
        print(f"[admin ai logs error] {e}")
        return {"items": []}


@router.post("/admin/sync/{board_id}")
def api_admin_sync_board(board_id: str):
    """从 data/*.json 同步指定版块到数据库"""
    from app.database import re_sync_board_from_json
    try:
        result = re_sync_board_from_json(board_id)
        return {"status": "ok", "board_id": board_id, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/sync")
def api_admin_sync_all():
    """从 data/*.json 同步全部版块到数据库"""
    from app.database import re_sync_all_from_json
    try:
        result = re_sync_all_from_json()
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---- admin articles（原有操作端点保留） ----

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

    # 防重入：该板块已在抓取中则拒绝重复启动
    existing = _crawl_logs.get(board_id)
    if existing and existing.get("status") == "running":
        return {"board_id": board_id, "status": "already_running", "message": f"{board_id} 正在抓取中，请勿重复启动"}

    _crawl_logs[board_id] = {
        "status": "running",
        "lines": [],
        "started_at": datetime.now().isoformat()
    }

    def _run():
        try:
            _crawl_logs[board_id]["lines"].append(f"[{board_id}] starting...")
            result = run_crawler(board_id, log_fn=lambda msg: _crawl_logs[board_id]["lines"].append(f"[{board_id}] {msg}"))
            _crawl_logs[board_id]["lines"].append(f"[{board_id}] done: {result.get('message', 'OK')}")
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
async def api_ai_extract(category: str = None, limit: int = 10):
    loop = asyncio.get_event_loop()
    try:
        from app.ai_extractor import process_pending_articles
        result = await loop.run_in_executor(
            _crawl_executor,
            lambda: process_pending_articles(category=category, limit=limit, auto_insert=True)
        )
        return result
    except Exception as e:
        # 失败也写入提取历史（容错：表不存在时忽略）
        try:
            from app.database import log_ai_extract
            log_ai_extract(category=category, limit=limit, total=0, inserted=0, failed=0, status="failed", message=str(e))
        except Exception:
            pass
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
def api_get_latest_news(limit: int = 10, group_by_board: bool = False):
    from app.database import get_latest_news
    return {"items": get_latest_news(limit, group_by_board=group_by_board)}

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


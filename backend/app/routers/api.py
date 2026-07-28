from fastapi import APIRouter, HTTPException
from app.database import get_board, list_boards, log_crawl

router = APIRouter(prefix="/api")

# 板块 → 爬虫模块映射（模块级别，所有路由共用）
CRAWLER_MODULES = {
    "rocket": "crawlers.rocket",
    "moon": "crawlers.moon",
    "semiconductor": "crawlers.semiconductor",
    "china-tech": "crawlers.china_tech",
    "mega-projects": "crawlers.mega_projects",
    "controlled-fusion": "crawlers.controlled_fusion",
    "finance": "crawlers.finance",
}


@router.post("/sync/rocket")
def api_sync_rocket_timeline():
    """手动同步 Launch API 数据到 rocket_timeline 表"""
    from app.database import sync_launch_api_to_timeline
    from app.database import sync_rocket_companies
    timeline_count = sync_launch_api_to_timeline()
    companies_count = sync_rocket_companies()
    return {"status": "ok", "timeline_synced": timeline_count, "companies_synced": companies_count}


@router.post("/sync/rocket-companies")
def api_sync_rocket_companies_only():
    """手动同步 LL2 API 数据到 rocket_companies 表"""
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
        raise HTTPException(status_code=404, detail=f"Board '{board_id}' not found")
    return data


@router.post("/crawl/{board_id}")
def api_crawl_board(board_id: str):
    """手动触发单个板块爬虫"""
    try:
        result = run_crawler(board_id)
        log_crawl(board_id, "success", result.get("message", "OK"))
        return {"board_id": board_id, "status": "success", "detail": result}
    except Exception as e:
        log_crawl(board_id, "failed", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crawl")
def api_crawl_all():
    """手动触发全部爬虫"""
    results = {}
    for bid in CRAWLER_MODULES:
        try:
            results[bid] = run_crawler(bid)
        except Exception as e:
            results[bid] = {"error": str(e)}
    return {"status": "done", "results": results}


# ---- 爬取数据查询 ----

@router.get("/articles/{board_id}")
def api_get_articles(board_id: str, limit: int = 20):
    """获取某个板块最近抓取的文章列表"""
    from app.database import get_recent_articles, get_articles_stats
    articles = get_recent_articles(board_id, limit)
    stats = get_articles_stats(board_id)
    return {"board_id": board_id, "stats": stats, "articles": articles}


@router.get("/last-updated")
def api_last_updated():
    """返回所有板块中最新的数据更新时间"""
    from app.database import get_global_last_updated
    return {"last_updated": get_global_last_updated()}


@router.get("/rocket-intro")
def api_get_rocket_intro():
    """返回火箭板块 AI 动态引言（HTML 片段）"""
    from app.database import get_rocket_intro
    return {"intro": get_rocket_intro()}


@router.get("/status/{board_id}")
def api_get_board_status(board_id: str):
    """查询某个板块的爬取状态（最近一次爬取时间、新增数量等）"""
    from app.database import get_board_status
    s = get_board_status(board_id)
    if s is None:
        return {"board_id": board_id, "status": "never_crawled"}
    return {"board_id": board_id, **s}


def run_crawler(board_id: str) -> dict:
    """复用现有爬虫 + 去重入库 + 状态记录"""
    import sys, os, json, importlib
    from app.database import (
        upsert_article, update_board_status, _classify_crawled_item,
        log_crawl
    )

    root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)

    mod_name = CRAWLER_MODULES.get(board_id)
    if not mod_name:
        raise ValueError(f"Unknown board: {board_id}")

    # 1. 运行所有爬虫函数
    mod = importlib.import_module(mod_name)
    total_new = 0
    total_sources = 0
    error_sources = 0
    sources_detail = {}

    for name in dir(mod):
        if not (name.startswith("crawl_") and callable(getattr(mod, name))):
            continue
        total_sources += 1
        source_name = name.replace("crawl_", "", 1)
        try:
            raw_result = getattr(mod, name)()
        except Exception as e:
            error_sources += 1
            sources_detail[source_name] = {"error": str(e), "new": 0}
            continue

        # 2. 统一化 + 去重入库
        items = raw_result if isinstance(raw_result, list) else [raw_result]
        new_for_source = 0

        for item in items:
            if not isinstance(item, dict):
                continue
            title, url, summary, date, raw_json = _classify_crawled_item(item)
            if not title.strip():
                continue  # 跳过无标题的条目

            is_new = upsert_article(
                board_id=board_id,
                source=source_name,
                title=title,
                url=url,
                summary=summary,
                date=date,
                raw_json=raw_json,
            )
            if is_new:
                new_for_source += 1

        total_new += new_for_source
        sources_detail[source_name] = {"new": new_for_source, "total_items": len(items)}

    # 3. 更新板块状态
    if total_new > 0:
        msg = f"+{total_new} new articles"
    else:
        msg = "no new data"
    update_board_status(board_id, total_new, total_sources, error_sources, msg)

    # 4. 写 crawl_log
    log_crawl(board_id, "success", msg)

    # 5. 后处理：火箭板块 → 同步结构化表
    timeline_new = 0
    companies_new = 0
    if board_id == "rocket":
        try:
            from app.database import sync_launch_api_to_timeline
            timeline_new = sync_launch_api_to_timeline()
        except Exception:
            pass
        try:
            from app.database import sync_rocket_companies
            companies_new = sync_rocket_companies()
        except Exception:
            pass
        # 6. LLM 更新引言
        try:
            from app.llm import update_rocket_intro_if_needed
            update_rocket_intro_if_needed()
        except Exception:
            pass

    return {
        "board_id": board_id,
        "sources": total_sources,
        "errors": error_sources,
        "new_items": total_new,
        "timeline_synced": timeline_new,
        "message": msg,
        "detail": sources_detail,
    }


BOARD_IDS = list(CRAWLER_MODULES.keys())


# ============================================================
#  AI 解读 + SQLite 同步（手动触发）
# ============================================================

@router.post("/ai-update")
def api_ai_update_all():
    """手动触发全量 AI 解读并同步到 SQLite"""
    import sys, os
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent.parent.parent  # taixing/
    sys.path.insert(0, str(project_root))
    import ai_update
    from app.database import re_sync_all_from_json

    result = ai_update.run_ai_update(base_dir=str(project_root))
    re_sync_all_from_json()
    return {"status": "ok", "ai_result": result}


@router.post("/ai-update/{board_id}")
def api_ai_update_board(board_id: str):
    """手动触发单个板块 AI 解读并同步到 SQLite"""
    import sys, os
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent.parent.parent  # taixing/
    sys.path.insert(0, str(project_root))
    import ai_update
    from app.database import re_sync_board_from_json

    if board_id not in ai_update.BOARDS:
        raise HTTPException(404, f"Unknown board: {board_id}")

    result = ai_update.run_ai_update(board_ids=[board_id], base_dir=str(project_root))
    if result["success"]:
        re_sync_board_from_json(board_id)
    return {"status": "ok", "ai_result": result}

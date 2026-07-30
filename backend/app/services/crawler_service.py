"""
爬虫服务 — run_crawler 从 api.py 提取而来
"""
import sys, os, json, importlib
from app.db.articles import upsert_article, _classify_crawled_item
from app.db.board_ops import update_board_status
from app.db.admin import log_crawl
from crawlers.crawler_registry import CRAWLER_MODULES


def run_crawler(board_id: str) -> dict:
    """复用现有爬虫 + 去重入库 + 状态记录"""
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
            from app.db.board_data import sync_launch_api_to_timeline
            timeline_new = sync_launch_api_to_timeline()
        except Exception:
            pass
        try:
            from app.db.board_data import sync_rocket_companies
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

"""
爬虫服务 — run_crawler 从 api.py 提取而来
"""
import sys, os, json, importlib
from app.db.articles import upsert_article, _classify_crawled_item
from app.db.board_ops import update_board_status
from app.db.admin import log_crawl
from app.db.board_data import upsert_launch_timeline
from crawlers.crawler_registry import CRAWLER_MODULES


def _run_macro(board_id: str, log_fn) -> dict:
    """宏观指标板块：仅运行 crawl_* 函数（各函数自行写入 data/macro.json），不入库"""
    import importlib
    mod = importlib.import_module("crawlers.macro")
    total_sources = 0
    error_sources = 0
    sources_detail = {}
    for name in dir(mod):
        if not (name.startswith("crawl_") and callable(getattr(mod, name))):
            continue
        total_sources += 1
        source_name = name.replace("crawl_", "", 1)
        log_fn(f"[{source_name}] 开始抓取...")
        try:
            getattr(mod, name)()
            sources_detail[source_name] = {"status": "ok"}
            log_fn(f"[{source_name}] 完成 ✓")
        except Exception as e:
            error_sources += 1
            sources_detail[source_name] = {"status": "error", "error": str(e)}
            log_fn(f"[{source_name}] 失败: {e}")
    msg = f"宏观指标已更新，{total_sources - error_sources}/{total_sources} 个数据源成功"
    try:
        from app.db.admin import log_crawl
        log_crawl(board_id, "success" if error_sources == 0 else "partial", msg)
    except Exception:
        pass
    return {
        "board_id": board_id,
        "sources": total_sources,
        "errors": error_sources,
        "new_items": 0,
        "timeline_synced": 0,
        "message": msg,
        "detail": sources_detail,
    }


def run_crawler(board_id: str, log_fn=None) -> dict:
    """复用现有爬虫 + 去重入库 + 状态记录

    log_fn: 可选回调（str -> None），每个数据源处理进度时调用，用于管理端实时日志
    """
    root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)

    def _log(msg: str):
        if log_fn:
            try:
                log_fn(msg)
            except Exception:
                pass
        else:
            print(msg)

    mod_name = CRAWLER_MODULES.get(board_id)
    if not mod_name:
        raise ValueError(f"Unknown board: {board_id}")

    # 0. 宏观指标板块特判：爬虫自行写入 data/macro.json，不入库、不更新板块状态
    if board_id == "macro":
        return _run_macro(board_id, _log)

    # 1. 运行所有爬虫函数
    mod = importlib.import_module(mod_name)
    total_new = 0
    timeline_new = 0
    total_sources = 0
    error_sources = 0
    sources_detail = {}

    for name in dir(mod):
        if not (name.startswith("crawl_") and callable(getattr(mod, name))):
            continue
        total_sources += 1
        source_name = name.replace("crawl_", "", 1)
        _log(f"[{source_name}] 开始抓取...")
        try:
            raw_result = getattr(mod, name)()
        except Exception as e:
            error_sources += 1
            sources_detail[source_name] = {"error": str(e), "new": 0}
            _log(f"[{source_name}] 失败: {e}")
            continue
        _log(f"[{source_name}] 抓取返回 {len(raw_result) if isinstance(raw_result, list) else 1} 条")

        # 2. 统一化 + 去重入库
        items = raw_result if isinstance(raw_result, list) else [raw_result]
        new_for_source = 0
        timeline_for_source = 0

        for item in items:
            if not isinstance(item, dict):
                continue

            if "timeline_id" in item:
                # 火箭发射日历条目（LL2 API）：结构与 rocket_launch_timeline 表字段一一对应，
                # 直接 upsert 到该表，不走通用新闻去重入库
                try:
                    if upsert_launch_timeline(item):
                        timeline_for_source += 1
                except Exception as e:
                    print(f"[crawler_service] 写入 rocket_launch_timeline 失败：{e}")
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
        timeline_new += timeline_for_source
        sources_detail[source_name] = {"new": new_for_source, "total_items": len(items)}
        if timeline_for_source:
            sources_detail[source_name]["timeline_synced"] = timeline_for_source
            _log(f"[{source_name}] 时间线同步 {timeline_for_source} 条")
        _log(f"[{source_name}] 新增 {new_for_source} 条")

    # 3. 更新板块状态
    if total_new > 0:
        msg = f"+{total_new} new articles"
    else:
        msg = "no new data"
    update_board_status(board_id, total_new, total_sources, error_sources, msg)

    # 4. 写 crawl_log
    log_crawl(board_id, "success", msg)

    # 5. 后处理：火箭板块 → 公司对比表（人工维护于 data/rocket.json）同步进数据库
    #    发射时间线（rocket_launch_timeline）已在上面抓取循环中随 crawl_rocket_launches 结果实时写入
    companies_new = 0
    if board_id == "rocket":
        try:
            from app.db.json_sync import sync_board_from_json
            result = sync_board_from_json("rocket")
            companies_new = result.get("rocket", {}).get("rocket_companies", 0)
        except Exception:
            pass
        # 6. LLM 更新引言（仅当出现新的已完成发射时才改写，见 maybe_trigger_rocket_ai）
        try:
            from app.llm import maybe_trigger_rocket_ai
            maybe_trigger_rocket_ai()
        except Exception as e:
            print(f"[AI] rocket AI 更新异常: {e}")

    return {
        "board_id": board_id,
        "sources": total_sources,
        "errors": error_sources,
        "new_items": total_new,
        "timeline_synced": timeline_new,
        "message": msg,
        "detail": sources_detail,
    }

"""
爬虫调度引擎
负责运行单个爬虫、分发多爬虫任务、生成爬取报告。
"""

import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from crawlers.crawler_registry import CRAWLER_FUNCTIONS
from crawlers.crawler_config import load_config, get_enabled_sources, BASE_DIR, DATA_DIR, CONFIG_FILE

REPORT_DIR = DATA_DIR / "_reports"

# 尝试导入数据库模块
sys.path.insert(0, str(BASE_DIR / "backend"))
try:
    from app.database import upsert_news_article, upsert_launch_timeline, log_crawl
    DB_AVAILABLE = True
except ImportError as e:
    print(f"[警告] 数据库模块导入失败：{e}")
    print("  将仅写入 JSON 文件，不写入数据库")
    DB_AVAILABLE = False


def run_crawler(src_cfg):
    """
    根据配置运行单个爬虫。
    返回 (items, auto_write) -- auto_write 表示是否直接写 JSON 而非返回 items。
    """
    crawler_name = src_cfg.get("crawler", "")
    crawler_func = CRAWLER_FUNCTIONS.get(crawler_name)

    if not crawler_func:
        print(f"  [错误] 爬虫函数 '{crawler_name}' 未注册，请在 crawler_registry.py 中添加")
        return [], False

    board_id = src_cfg.get("_board_id", "unknown")
    board_name = src_cfg.get("_board_name", "unknown")
    auto_write = src_cfg.get("_auto_write", False)

    print(f"\n{'='*60}")
    print(f"  [{board_id}] {board_name} -> {src_cfg.get('name','')} ({crawler_name})")
    print(f"  类型: {src_cfg.get('type','?')} | {src_cfg.get('description','')}")
    print(f"{'='*60}")

    try:
        result = crawler_func()
    except Exception as e:
        print(f"  [错误] 爬虫执行异常: {e}")
        return [], False

    if result is None:
        print(f"  [跳过] 无数据返回")
        return [], False

    if auto_write:
        print(f"  [完成] 已自动写入数据文件")
        return [], True

    if isinstance(result, list):
        db_count = 0
        for item in result:
            if DB_AVAILABLE:
                try:
                    if "timeline_id" in item:
                        # 火箭发射日历条目（LL2 API）：直接写入 rocket_launch_timeline 表，
                        # 结构与该表字段一一对应，不再套壳塞进 raw_articles 通用新闻池
                        upsert_launch_timeline(item)
                    elif "news_id" in item:
                        upsert_news_article(item)
                    else:
                        url = item.get("url", "")
                        # items without url/title (e.g. launch calendar): build stable unique key from timeline_id/mission_name
                        dedup_key = url or item.get("timeline_id") or item.get("news_id") or item.get("title") or item.get("mission_name") or item.get("name") or ""
                        news_id = hashlib.sha256(str(dedup_key).encode()).hexdigest()[:16]
                        title = item.get("title") or item.get("mission_name") or ""
                        new_item = {
                            "news_id": news_id,
                            "source_name": src_cfg.get("name", ""),
                            "source_url": url,
                            "title": title,
                            "raw_content": item.get("summary", ""),
                            "summary": "",
                            "cover_image": item.get("image_url", ""),
                            "images": "[]",
                            "tags": "[]",
                            "category": board_id,
                            "hot_score": 0,
                            "sentiment": "neutral",
                            "language": "en",
                            "status": "pending",
                        }
                        upsert_news_article(new_item)
                    db_count += 1
                except Exception as e:
                    print(f"  [数据库] 写入失败：{e}")
        print(f"  [完成] 获取 {len(result)} 条数据，写入数据库 {db_count} 条")
    else:
        print(f"  [完成] 返回非列表结果: {type(result).__name__}")

    return result if isinstance(result, list) else [], False


def dispatch_crawlers(config, board_ids=None, source_ids=None):
    """
    调度器：根据配置运行所有启用的爬虫。
    返回按板块分组的 items 字典。
    """
    sources = get_enabled_sources(config, board_ids=board_ids, source_ids=source_ids)

    if not sources:
        print("没有找到匹配的数据源。用 --list 查看可用数据源。")
        return {}

    board_plan = {}
    for src in sources:
        bid = src["_board_id"]
        if bid not in board_plan:
            board_plan[bid] = []
        board_plan[bid].append(src["name"])

    print(f"\n{'='*60}")
    print(f"  爬取计划 -- {len(sources)} 个数据源，{len(board_plan)} 个板块")
    print(f"{'='*60}")
    for bid, names in board_plan.items():
        print(f"  [{bid}] {' -> '.join(names)}")
    print()

    all_items = []
    board_results = {}
    board_ids_list = list(board_plan.keys())

    for bid in board_ids_list:
        board_srcs = [s for s in sources if s["_board_id"] == bid]
        for i, src in enumerate(board_srcs):
            items, auto_written = run_crawler(src)

            if not auto_written:
                all_items.extend(items)
                if bid not in board_results:
                    board_results[bid] = []
                board_results[bid].extend(items)

            sleep_sec = src.get("sleep_after", 1)
            if sleep_sec > 0 and (i < len(board_srcs) - 1 or bid != board_ids_list[-1]):
                time.sleep(sleep_sec)

    return board_results


def generate_report(all_items):
    """生成结构化爬取报告"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")

    boards = {}
    for item in all_items:
        board = item.get("board", "other")
        if board not in boards:
            boards[board] = []
        boards[board].append(item)

    report = {
        "generated_at": datetime.now().isoformat(),
        "total_items": len(all_items),
        "by_board": {k: len(v) for k, v in boards.items()},
        "items": all_items,
    }

    report_file = REPORT_DIR / f"crawl_report_{ts}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("爬取报告")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总计: {len(all_items)} 条")
    print()
    for board, items in sorted(boards.items()):
        print(f"  [{board}] {len(items)} 条")
        for item in items[:3]:
            date = item.get("date", "?")
            title = item.get("title", "")[:55]
            print(f"    {date:<12} | {title}")
        if len(items) > 3:
            print(f"    ... 还有 {len(items)-3} 条")
    print()
    print(f"报告文件: {report_file}")
    print("=" * 60)

    return report_file

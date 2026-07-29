#!/usr/bin/env python3
"""
钛星网站数据爬虫脚本 — 配置驱动版
数据源由 data_sources.json 定义，按7个板块分类。
爬虫函数位于 crawlers/ 目录下各模块中。

用法：
    python fetch_data.py                   # 全部抓取
    python fetch_data.py --rocket          # 只抓火箭板块
    python fetch_data.py --fusion --ai     # 抓核聚变+AI板块
    python fetch_data.py --list            # 列出所有数据源
    python fetch_data.py --list --rocket   # 只列出火箭板块数据源
    python fetch_data.py --source smic     # 只抓单个数据源（by id）
    python fetch_data.py --report          # 只生成报告

配置：编辑 data_sources.json 增删数据源
依赖：pip install requests beautifulsoup4 lxml
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# ============ 路径配置 ============
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = DATA_DIR / "_reports"
CONFIG_FILE = BASE_DIR / "data_sources.json"

# 添加 backend 到 Python 路径，以便导入数据库模块
sys.path.insert(0, str(BASE_DIR / "backend"))
try:
    from app.database import upsert_article, log_crawl
    DB_AVAILABLE = True
except ImportError as e:
    print(f"[警告] 数据库模块导入失败：{e}")
    print("  将仅写入 JSON 文件，不写入数据库")
    DB_AVAILABLE = False


# ============ 配置加载器 ============

def load_config():
    """加载 data_sources.json 配置文件"""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_enabled_sources(config, board_ids=None, source_ids=None):
    """
    从配置中获取启用的数据源列表。
    - board_ids: 要抓取的板块列表，None 表示全部
    - source_ids: 要抓取的单个数据源 id 列表，None 表示全部
    """
    sources = []
    boards = config.get("boards", {})

    for board_id, board_cfg in boards.items():
        if board_ids and board_id not in board_ids:
            continue

        for src in board_cfg.get("sources", []):
            if not src.get("enabled", True):
                continue
            if source_ids and src["id"] not in source_ids:
                continue

            # 注入板块信息
            src["_board_id"] = board_id
            src["_board_name"] = board_cfg.get("name", board_id)
            src["_output_file"] = board_cfg.get("output_file", "")
            src["_auto_write"] = board_cfg.get("auto_write", False)
            sources.append(src)

    return sources


def list_sources(config, board_ids=None):
    """列出数据源（用于 --list 参数）"""
    sources = get_enabled_sources(config, board_ids=board_ids)
    boards = config.get("boards", {})

    if board_ids:
        boards = {k: v for k, v in boards.items() if k in board_ids}

    for board_id, board_cfg in boards.items():
        print(f"\n{'='*60}")
        print(f"  [{board_id}] {board_cfg.get('name', '')} ({board_cfg.get('name_en', '')})")
        print(f"  输出: {board_cfg.get('output_file', 'N/A')}")
        print(f"{'='*60}")
        for src in board_cfg.get("sources", []):
            status = "✓" if src.get("enabled", True) else "✗ 禁用"
            print(f"  {status} {src['id']:<20} [{src.get('type','?')}] {src.get('name','')}")
            print(f"        爬虫: {src.get('crawler','')}() — {src.get('description','')}")

    total = sum(len(b.get("sources", [])) for b in boards.values())
    enabled = len(sources)
    print(f"\n总计: {enabled}/{total} 个数据源启用")
    print(f"配置文件: {CONFIG_FILE}")


# ============ 爬虫函数注册表 ============
# 从 crawlers/ 目录下各模块导入爬虫函数
# 配置文件中的 crawler 字段对应这里的 key，新增爬虫只需在此注册

from crawlers.rocket import crawl_rocket_launches, crawl_rocket_news_snapi
from crawlers.moon import crawl_nasa_artemis
from crawlers.controlled_fusion import crawl_iter, crawl_cfs, crawl_asipp
from crawlers.semiconductor import crawl_smic, crawl_smee
from crawlers.china_tech import crawl_anthropic, crawl_deepseek, crawl_moonshot, crawl_openai
from crawlers.mega_projects import crawl_china_railway
from crawlers.finance import crawl_exchange_rates, crawl_fed_rate

CRAWLER_REGISTRY = {
    # 火箭板块
    "crawl_rocket_launches": crawl_rocket_launches,
    "crawl_rocket_news_snapi": crawl_rocket_news_snapi,
    # 登月板块
    "crawl_nasa_artemis": crawl_nasa_artemis,
    # 核聚变板块
    "crawl_iter": crawl_iter,
    "crawl_cfs": crawl_cfs,
    "crawl_asipp": crawl_asipp,
    # 半导体板块
    "crawl_smic": crawl_smic,
    "crawl_smee": crawl_smee,
    # AI 板块
    "crawl_anthropic": crawl_anthropic,
    "crawl_deepseek": crawl_deepseek,
    "crawl_moonshot": crawl_moonshot,
    "crawl_openai": crawl_openai,
    # 大工程板块
    "crawl_china_railway": crawl_china_railway,
    # 金融板块
    "crawl_exchange_rates": crawl_exchange_rates,
    "crawl_fed_rate": crawl_fed_rate,
}


# ============ 报告生成 ============

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


# ============ 调度引擎 ============

def run_crawler(src_cfg):
    """
    根据配置运行单个爬虫。
    返回 (items, auto_write) — auto_write 表示是否直接写 JSON 而非返回 items。
    """
    crawler_name = src_cfg.get("crawler", "")
    crawler_func = CRAWLER_REGISTRY.get(crawler_name)

    if not crawler_func:
        print(f"  [错误] 爬虫函数 '{crawler_name}' 未注册，请在 CRAWLER_REGISTRY 中添加")
        return [], False

    board_id = src_cfg.get("_board_id", "unknown")
    board_name = src_cfg.get("_board_name", "unknown")
    auto_write = src_cfg.get("_auto_write", False)

    print(f"\n{'─'*60}")
    print(f"  [{board_id}] {board_name} → {src_cfg.get('name','')} ({crawler_name})")
    print(f"  类型: {src_cfg.get('type','?')} | {src_cfg.get('description','')}")
    print(f"{'─'*60}")

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
            if "board" not in item:
                item["board"] = board_id
            # 写入数据库（raw_articles 表）
            if DB_AVAILABLE:
                try:
                    upsert_article(
                        board_id=board_id,
                        source=src_cfg.get("name", ""),
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        summary=item.get("summary", ""),
                        date=item.get("date", ""),
                        raw_json=json.dumps(item, ensure_ascii=False),
                    )
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
    print(f"  爬取计划 — {len(sources)} 个数据源，{len(board_plan)} 个板块")
    print(f"{'='*60}")
    for bid, names in board_plan.items():
        print(f"  [{bid}] {' → '.join(names)}")
    print()

    all_items = []
    board_results = {}

    for bid in board_plan:
        board_srcs = [s for s in sources if s["_board_id"] == bid]
        for i, src in enumerate(board_srcs):
            items, auto_written = run_crawler(src)

            if auto_written:
                pass
            else:
                all_items.extend(items)
                if bid not in board_results:
                    board_results[bid] = []
                board_results[bid].extend(items)

            sleep_sec = src.get("sleep_after", 1)
            if sleep_sec > 0 and (i < len(board_srcs) - 1 or bid != list(board_plan.keys())[-1]):
                time.sleep(sleep_sec)

    return board_results


# ============ 主入口 ============

def main():
    if not CONFIG_FILE.exists():
        print(f"错误: 配置文件不存在: {CONFIG_FILE}")
        print("请先创建 data_sources.json 配置文件")
        sys.exit(1)

    config = load_config()
    valid_boards = set(config.get("_boards", []))

    args = sys.argv[1:]

    # --list: 列出数据源
    if "--list" in args:
        board_ids = set()
        for b in valid_boards:
            if f"--{b}" in args:
                board_ids.add(b)
        list_sources(config, board_ids=board_ids if board_ids else None)
        return

    # 确定要抓取的板块
    board_ids = set()
    source_ids = set()
    run_all = not args or "--all" in args

    for arg in args:
        arg_clean = arg.lstrip("-")
        if arg_clean in valid_boards:
            board_ids.add(arg_clean)
        elif arg.startswith("--source="):
            source_ids.add(arg.split("=", 1)[1])

    if not board_ids and not source_ids:
        run_all = True

    if run_all:
        board_ids = valid_boards

    print("=" * 60)
    print(f"钛星数据爬虫 (配置驱动) - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"配置文件: {CONFIG_FILE}")
    print("=" * 60)

    board_results = dispatch_crawlers(
        config,
        board_ids=board_ids if board_ids else None,
        source_ids=source_ids if source_ids else None,
    )

    show_report = "--report" in args or run_all or (not args)
    if show_report and board_results:
        all_items = []
        for items in board_results.values():
            all_items.extend(items)
        if all_items:
            generate_report(all_items)

    total = sum(len(v) for v in board_results.values())
    print(f"\n{'='*60}")
    print(f"  全部完成 — {total} 条数据，{len(board_results)} 个板块")
    for bid, items in board_results.items():
        print(f"    [{bid}] {len(items)} 条")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

"""
爬虫 CLI 入口
处理命令行参数解析，调度爬虫执行。
"""

import sys
from datetime import datetime

from crawlers.crawler_registry import BOARD_IDS
from crawlers.crawler_config import load_config, list_sources, CONFIG_FILE
from crawlers.crawler_engine import dispatch_crawlers, generate_report


def main():
    """CLI 主入口"""
    if not CONFIG_FILE.exists():
        print(f"错误: 配置文件不存在: {CONFIG_FILE}")
        print("请先创建 data_sources.json 配置文件")
        sys.exit(1)

    config = load_config()
    valid_boards = set(BOARD_IDS)

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

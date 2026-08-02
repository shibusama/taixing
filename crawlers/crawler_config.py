"""
爬虫配置模块
从 data_sources.json 加载配置，提供配置查询接口。
"""

import json
from pathlib import Path

from crawlers.crawler_registry import BOARD_IDS

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = BASE_DIR / "data_sources.json"


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
            src["_auto_write"] = src.get("auto_write", board_cfg.get("auto_write", False))
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
            status = "[ON]" if src.get("enabled", True) else "[OFF]禁用"
            print(f"  {status} {src['id']:<20} [{src.get('type','?')}] {src.get('name','')}")
            print(f"        爬虫: {src.get('crawler','')}() — {src.get('description','')}")
    total = sum(len(b.get("sources", [])) for b in boards.values())
    enabled = len(sources)
    print(f"\n总计: {enabled}/{total} 个数据源启用")
    print(f"配置文件: {CONFIG_FILE}")

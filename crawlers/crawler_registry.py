"""
爬虫共享注册表 - 统一的爬虫函数和板块注册

供 fetch_data.py (CLI) 和 backend (API/调度) 统一引用。
新增爬虫只需在此注册，无需修改两个地方。
"""

from typing import Dict, Callable, List, Optional

# ============ 板块 → 模块路径映射 ============

CRAWLER_MODULES: Dict[str, str] = {
    "rocket": "crawlers.rocket",
    "moon": "crawlers.moon",
    "semiconductor": "crawlers.semiconductor",
    "china-tech": "crawlers.china_tech",
    "mega-projects": "crawlers.mega_projects",
    "controlled-fusion": "crawlers.controlled_fusion",
    "finance": "crawlers.finance",
}

BOARD_IDS: list[str] = list(CRAWLER_MODULES.keys())


# ============ 爬虫函数注册表 ============
# 显式导入并注册，保持可追踪性

from crawlers.rocket import crawl_rocket_launches, crawl_rocket_news_snapi
from crawlers.moon import crawl_nasa_artemis
from crawlers.controlled_fusion import crawl_iter, crawl_cfs, crawl_asipp
from crawlers.semiconductor import crawl_smic, crawl_smee
from crawlers.china_tech import crawl_anthropic, crawl_deepseek, crawl_moonshot, crawl_openai
from crawlers.mega_projects import crawl_china_railway
from crawlers.finance import crawl_exchange_rates, crawl_fed_rate

CRAWLER_FUNCTIONS: Dict[str, Callable] = {
    "crawl_rocket_launches": crawl_rocket_launches,
    "crawl_rocket_news_snapi": crawl_rocket_news_snapi,
    "crawl_nasa_artemis": crawl_nasa_artemis,
    "crawl_iter": crawl_iter,
    "crawl_cfs": crawl_cfs,
    "crawl_asipp": crawl_asipp,
    "crawl_smic": crawl_smic,
    "crawl_smee": crawl_smee,
    "crawl_anthropic": crawl_anthropic,
    "crawl_deepseek": crawl_deepseek,
    "crawl_moonshot": crawl_moonshot,
    "crawl_openai": crawl_openai,
    "crawl_china_railway": crawl_china_railway,
    "crawl_exchange_rates": crawl_exchange_rates,
    "crawl_fed_rate": crawl_fed_rate,
}


# ============ 辅助函数 ============

def get_crawl_function(name: str) -> Optional[Callable]:
    """按名称获取爬虫函数"""
    return CRAWLER_FUNCTIONS.get(name)


def get_board_module_path(board_id: str) -> Optional[str]:
    """获取板块对应的模块导入路径"""
    return CRAWLER_MODULES.get(board_id)


def iter_board_crawl_functions(board_id: str) -> list[tuple[str, Callable]]:
    """遍历板块下所有爬虫函数，返回 (function_name, function) 列表"""
    import importlib
    mod_path = CRAWLER_MODULES.get(board_id)
    if not mod_path:
        return []
    try:
        mod = importlib.import_module(mod_path)
    except ImportError:
        return []
    results: list[tuple[str, Callable]] = []
    for name in dir(mod):
        if name.startswith("crawl_") and callable(getattr(mod, name)):
            results.append((name, getattr(mod, name)))
    return results


# ============ generic RSS sources auto-registration ============
def _register_rss_sources():
    """Scan data_sources.json for type=rss sources and register crawl_rss_<id>."""
    import json
    from pathlib import Path
    cfg_file = Path(__file__).parent.parent / "data_sources.json"
    try:
        cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
        from crawlers.rss import make_rss_crawler
    except Exception as e:
        print(f"[registry] rss init failed: {e}")
        return
    for board_id, board_cfg in cfg.get("boards", {}).items():
        for src in board_cfg.get("sources", []):
            if src.get("type") != "rss":
                continue
            sid = src.get("id", "")
            func_name = "crawl_rss_" + sid
            CRAWLER_FUNCTIONS[func_name] = make_rss_crawler(
                feed_url=src.get("feed_url", ""),
                source_name=src.get("name", sid),
                category=board_id,
                board_id=board_id,
                language=src.get("language", "en"),
                limit=src.get("limit", 20),
            )


_register_rss_sources()

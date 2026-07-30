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

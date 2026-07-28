"""
钛星科技新闻站 - 数据库模块
使用 Supabase (Coze 内置数据库)

表名和列名严格与 model.py 保持一致：
  - raw_articles: board, source, title, url, content, published_at, crawled_at
  - crawl_logs: board, source, status, message, articles_count, created_at
  - board_status: board, last_crawl_at, articles_count, sources_count, updated_at
  - rocket_companies, rocket_timeline, moon_highlights, ...
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from supabase import create_client, Client

# Supabase 客户端（Coze 内置数据库）
_supabase: Optional[Client] = None


def get_supabase() -> Client:
    """获取 Supabase 客户端"""
    global _supabase
    if _supabase is None:
        supabase_url = os.environ.get("COZE_SUPABASE_URL")
        supabase_key = os.environ.get("COZE_SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("COZE_SUPABASE_ANON_KEY")

        if not supabase_url or not supabase_key:
            raise RuntimeError("Supabase 环境变量未配置：需要 COZE_SUPABASE_URL 和 COZE_SUPABASE_ANON_KEY")

        _supabase = create_client(supabase_url, supabase_key)
    return _supabase


def init_db():
    """初始化数据库（Supabase 不需要手动创建表）"""
    try:
        sb = get_supabase()
        print("数据库连接成功（Supabase）")
    except Exception as e:
        print(f"数据库连接失败：{e}")
        raise


# ============ board_status ============

def get_board_status(board_id: str) -> Optional[Dict]:
    """获取板块状态"""
    sb = get_supabase()
    result = sb.table("board_status").select("*").eq("board", board_id).execute()
    return result.data[0] if result.data else None


def get_all_board_status() -> List[Dict]:
    """获取所有板块状态"""
    sb = get_supabase()
    result = sb.table("board_status").select("*").execute()
    return result.data


def update_board_status(board_id: str, total_new: int = 0, total_sources: int = 0, error_sources: int = 0, msg: str = ""):
    """更新板块状态（由 run_crawler 调用）"""
    sb = get_supabase()
    now = datetime.now().isoformat()

    existing = get_board_status(board_id)
    if existing:
        # 累加文章数
        new_count = (existing.get("articles_count") or 0) + total_new
        sb.table("board_status").update({
            "articles_count": new_count,
            "sources_count": total_sources,
            "last_crawl_at": now,
            "updated_at": now,
        }).eq("board", board_id).execute()
    else:
        sb.table("board_status").insert({
            "board": board_id,
            "articles_count": total_new,
            "sources_count": total_sources,
            "last_crawl_at": now,
        }).execute()


# ============ boards 兼容（get_board / list_boards） ============

def get_board(board_id: str) -> Optional[Dict]:
    """获取板块信息（兼容 api.py）"""
    sb = get_supabase()
    result = sb.table("board_status").select("*").eq("board", board_id).execute()
    return result.data[0] if result.data else None


def list_boards() -> List[Dict]:
    """获取所有板块（兼容 api.py）"""
    sb = get_supabase()
    result = sb.table("board_status").select("*").execute()
    return result.data


# ============ raw_articles ============

def get_raw_articles(board_id: str = None, limit: int = 50) -> List[Dict]:
    """获取原始文章"""
    sb = get_supabase()
    query = sb.table("raw_articles").select("*")
    if board_id:
        query = query.eq("board", board_id)
    result = query.order("crawled_at", desc=True).limit(limit).execute()
    return result.data


def insert_raw_article(article: Dict) -> int:
    """插入原始文章"""
    sb = get_supabase()
    result = sb.table("raw_articles").insert(article).execute()
    if result.data:
        return result.data[0].get("id", 0)
    return 0


def upsert_article(board_id: str, source: str, title: str, url: str, summary: str = "", date: str = "", raw_json: str = "") -> bool:
    """插入或更新文章（去重：按 board + url）。返回 True 表示新增。"""
    sb = get_supabase()
    # 检查是否已存在
    existing = sb.table("raw_articles").select("id").eq("board", board_id).eq("url", url).limit(1).execute()
    if existing.data:
        return False  # 已存在，跳过

    sb.table("raw_articles").insert({
        "board": board_id,
        "source": source,
        "title": title,
        "url": url,
        "content": summary or raw_json or "",
        "published_at": date or None,
    }).execute()
    return True


def update_article(article_id: int, **kwargs):
    """更新文章"""
    sb = get_supabase()
    sb.table("raw_articles").update(kwargs).eq("id", article_id).execute()


def delete_article(article_id: int):
    """删除文章"""
    sb = get_supabase()
    sb.table("raw_articles").delete().eq("id", article_id).execute()


def get_recent_articles(board_id: str = None, limit: int = 10) -> List[Dict]:
    """获取最近文章"""
    sb = get_supabase()
    query = sb.table("raw_articles").select("*")
    if board_id:
        query = query.eq("board", board_id)
    result = query.order("crawled_at", desc=True).limit(limit).execute()
    return result.data


def get_articles_stats(board_id: str = None) -> Dict:
    """获取文章统计"""
    sb = get_supabase()
    query = sb.table("raw_articles").select("id")
    if board_id:
        query = query.eq("board", board_id)
    result = query.execute()
    return {"total": len(result.data)}


# ============ crawl_logs ============

def log_crawl(board_id: str, status: str, message: str = "", items_count: int = 0):
    """记录爬虫日志"""
    sb = get_supabase()
    sb.table("crawl_logs").insert({
        "board": board_id,
        "source": "scheduler",
        "status": status,
        "message": message,
        "articles_count": items_count,
    }).execute()


def get_crawl_logs(board_id: str = None, limit: int = 20) -> List[Dict]:
    """获取爬虫日志"""
    sb = get_supabase()
    query = sb.table("crawl_logs").select("*")
    if board_id:
        query = query.eq("board", board_id)
    result = query.order("created_at", desc=True).limit(limit).execute()
    return result.data


# ============ 全局更新时间 ============

def get_global_last_updated() -> str:
    """获取全局最后更新时间"""
    sb = get_supabase()
    result = sb.table("crawl_logs").select("created_at").order("created_at", desc=True).limit(1).execute()
    if result.data:
        return result.data[0].get("created_at", "")
    return ""


# ============ 爬虫分类工具 ============

def _classify_crawled_item(item: dict) -> tuple:
    """从爬虫返回的 dict 中提取标准化字段。返回 (title, url, summary, date, raw_json)"""
    title = str(item.get("title", "") or "").strip()
    url = str(item.get("url", "") or item.get("link", "") or "").strip()
    summary = str(item.get("summary", "") or item.get("description", "") or item.get("content", "") or "").strip()
    date = str(item.get("date", "") or item.get("published_at", "") or item.get("pubDate", "") or "").strip()
    raw_json = json.dumps(item, ensure_ascii=False) if item else ""
    return title, url, summary, date, raw_json


# ============ 火箭板块 ============

def get_rocket_companies() -> List[Dict]:
    """获取可回收火箭公司列表"""
    sb = get_supabase()
    result = sb.table("rocket_companies").select("*").execute()
    return result.data


def get_rocket_timeline() -> List[Dict]:
    """获取可回收火箭时间线"""
    sb = get_supabase()
    result = sb.table("rocket_timeline").select("*").order("event_date", desc=True).execute()
    return result.data


def get_rocket_intro() -> Optional[Dict]:
    """获取火箭简介（从 board_status 读取）"""
    sb = get_supabase()
    result = sb.table("board_status").select("*").eq("board", "rocket").execute()
    if result.data:
        return {"intro": result.data[0].get("last_crawl_at", "")}
    return None


def set_rocket_intro(intro: str):
    """设置火箭简介（写入 board_status 的 last_crawl_at 字段暂存）"""
    sb = get_supabase()
    existing = get_board_status("rocket")
    if existing:
        sb.table("board_status").update({"last_crawl_at": intro}).eq("board", "rocket").execute()


def sync_launch_api_to_timeline():
    """同步发射 API 到时间线（占位）"""
    return 0


def sync_rocket_companies():
    """同步火箭公司数据（占位）"""
    return 0


# ============ 登月板块 ============

def get_moon_highlights() -> List[Dict]:
    """获取登月亮点"""
    sb = get_supabase()
    result = sb.table("moon_highlights").select("*").execute()
    return result.data


def get_moon_comparison() -> List[Dict]:
    """获取中美登月对比"""
    sb = get_supabase()
    result = sb.table("moon_comparison").select("*").execute()
    return result.data


# ============ 半导体板块 ============

def get_semiconductor_highlights() -> List[Dict]:
    """获取半导体亮点"""
    sb = get_supabase()
    # model.py 中是 semiconductor_companies
    result = sb.table("semiconductor_companies").select("*").execute()
    return result.data


def get_semiconductor_tab_highlights() -> List[Dict]:
    """获取半导体 Tab 亮点"""
    sb = get_supabase()
    result = sb.table("semiconductor_companies").select("*").execute()
    return result.data


def get_semiconductor_tab_progress() -> List[Dict]:
    """获取半导体 Tab 进展"""
    sb = get_supabase()
    result = sb.table("semiconductor_timeline").select("*").execute()
    return result.data


# ============ 中国科技 AI ============

def get_china_tech_highlights() -> List[Dict]:
    """获取中国科技 AI 亮点"""
    sb = get_supabase()
    result = sb.table("china_tech_companies").select("*").execute()
    return result.data


def get_china_tech_llm() -> List[Dict]:
    """获取中国科技 AI 大模型"""
    sb = get_supabase()
    result = sb.table("china_tech_companies").select("*").execute()
    return result.data


# ============ 大工程 ============

def get_mega_projects() -> List[Dict]:
    """获取大工程列表"""
    sb = get_supabase()
    result = sb.table("mega_projects").select("*").execute()
    return result.data


def get_mega_project_highlights() -> List[Dict]:
    """获取大工程亮点"""
    sb = get_supabase()
    result = sb.table("mega_projects").select("*").execute()
    return result.data


def get_mega_project_milestones() -> List[Dict]:
    """获取大工程里程碑"""
    sb = get_supabase()
    result = sb.table("mega_project_timeline").select("*").execute()
    return result.data


# ============ 核聚变 ============

def get_fusion_highlights() -> List[Dict]:
    """获取核聚变亮点"""
    sb = get_supabase()
    result = sb.table("fusion_projects").select("*").execute()
    return result.data


def get_fusion_timeline() -> List[Dict]:
    """获取核聚变时间线"""
    sb = get_supabase()
    result = sb.table("fusion_timeline").select("*").execute()
    return result.data


# ============ 科技资本 ============

def get_finance_grids() -> List[Dict]:
    """获取科技资本网格数据"""
    sb = get_supabase()
    result = sb.table("finance_companies").select("*").execute()
    return result.data


def get_finance_highlights() -> List[Dict]:
    """获取科技资本亮点"""
    sb = get_supabase()
    result = sb.table("finance_companies").select("*").execute()
    return result.data


def get_finance_sections() -> List[Dict]:
    """获取科技资本板块"""
    sb = get_supabase()
    result = sb.table("finance_funding_events").select("*").execute()
    return result.data


# ============ 同步 / 重同步 ============

def re_sync_all_from_json():
    """从 JSON 重新同步所有数据（占位）"""
    pass


def re_sync_board_from_json(board_id: str):
    """从 JSON 重新同步板块数据（占位）"""
    pass


# ============ 兼容旧代码 ============

def get_cursor():
    """获取数据库游标（兼容旧代码，Supabase 下不可用）"""
    return None


def _list(data):
    """列表转换（兼容旧代码）"""
    return data if isinstance(data, list) else []

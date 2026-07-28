"""
钛星科技新闻站 - 数据库模块
使用 Supabase (Coze 内置数据库)
"""
import os
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
    # 验证连接
    try:
        sb = get_supabase()
        sb.table("health_check").select("*").limit(1).execute()
        print("数据库连接成功（Supabase）")
    except Exception as e:
        print(f"数据库连接失败：{e}")
        raise


# ============ 数据访问层 ============

def get_board_status(board_id: str) -> Optional[Dict]:
    """获取板块状态"""
    sb = get_supabase()
    result = sb.table("board_status").select("*").eq("board_id", board_id).execute()
    return result.data[0] if result.data else None


def get_all_board_status() -> List[Dict]:
    """获取所有板块状态"""
    sb = get_supabase()
    result = sb.table("board_status").select("*").execute()
    return result.data


def update_board_status(board_id: str, **kwargs):
    """更新板块状态"""
    sb = get_supabase()
    kwargs["board_id"] = board_id
    kwargs["updated_at"] = datetime.now().isoformat()
    
    # 检查是否存在
    existing = get_board_status(board_id)
    if existing:
        sb.table("board_status").update(kwargs).eq("board_id", board_id).execute()
    else:
        kwargs["created_at"] = datetime.now().isoformat()
        sb.table("board_status").insert(kwargs).execute()


def get_rocket_companies() -> List[Dict]:
    """获取可回收火箭公司列表"""
    sb = get_supabase()
    result = sb.table("rocket_companies").select("*").order("sort_order").execute()
    return result.data


def get_rocket_timeline() -> List[Dict]:
    """获取可回收火箭时间线"""
    sb = get_supabase()
    result = sb.table("rocket_timeline").select("*").order("event_date", desc=True).execute()
    return result.data


def get_moon_highlights() -> List[Dict]:
    """获取登月亮点"""
    sb = get_supabase()
    result = sb.table("moon_highlights").select("*").order("sort_order").execute()
    return result.data


def get_moon_comparison() -> List[Dict]:
    """获取中美登月对比"""
    sb = get_supabase()
    result = sb.table("moon_comparison").select("*").order("sort_order").execute()
    return result.data


def get_semiconductor_highlights() -> List[Dict]:
    """获取半导体亮点"""
    sb = get_supabase()
    result = sb.table("semiconductor_highlights").select("*").order("sort_order").execute()
    return result.data


def get_semiconductor_tab_highlights() -> List[Dict]:
    """获取半导体 Tab 亮点"""
    sb = get_supabase()
    result = sb.table("semiconductor_tab_highlights").select("*").order("sort_order").execute()
    return result.data


def get_semiconductor_tab_progress() -> List[Dict]:
    """获取半导体 Tab 进展"""
    sb = get_supabase()
    result = sb.table("semiconductor_tab_progress").select("*").order("sort_order").execute()
    return result.data


def get_china_tech_highlights() -> List[Dict]:
    """获取中国科技 AI 亮点"""
    sb = get_supabase()
    result = sb.table("china_tech_highlights").select("*").order("sort_order").execute()
    return result.data


def get_china_tech_llm() -> List[Dict]:
    """获取中国科技 AI 大模型"""
    sb = get_supabase()
    result = sb.table("china_tech_llm").select("*").order("sort_order").execute()
    return result.data


def get_mega_projects() -> List[Dict]:
    """获取大工程列表"""
    sb = get_supabase()
    result = sb.table("mega_projects").select("*").order("sort_order").execute()
    return result.data


def get_mega_project_highlights() -> List[Dict]:
    """获取大工程亮点"""
    sb = get_supabase()
    result = sb.table("mega_project_highlights").select("*").order("sort_order").execute()
    return result.data


def get_mega_project_milestones() -> List[Dict]:
    """获取大工程里程碑"""
    sb = get_supabase()
    result = sb.table("mega_project_milestones").select("*").order("sort_order").execute()
    return result.data


def get_fusion_highlights() -> List[Dict]:
    """获取核聚变亮点"""
    sb = get_supabase()
    result = sb.table("fusion_highlights").select("*").order("sort_order").execute()
    return result.data


def get_fusion_timeline() -> List[Dict]:
    """获取核聚变时间线"""
    sb = get_supabase()
    result = sb.table("fusion_timeline").select("*").order("event_date", desc=True).execute()
    return result.data


def get_finance_grids() -> List[Dict]:
    """获取科技资本网格数据"""
    sb = get_supabase()
    result = sb.table("finance_grids").select("*").order("sort_order").execute()
    return result.data


def get_finance_highlights() -> List[Dict]:
    """获取科技资本亮点"""
    sb = get_supabase()
    result = sb.table("finance_highlights").select("*").order("sort_order").execute()
    return result.data


def get_finance_sections() -> List[Dict]:
    """获取科技资本板块"""
    sb = get_supabase()
    result = sb.table("finance_sections").select("*").order("sort_order").execute()
    return result.data


def get_raw_articles(board_id: str = None, limit: int = 50) -> List[Dict]:
    """获取原始文章"""
    sb = get_supabase()
    query = sb.table("raw_articles").select("*")
    if board_id:
        query = query.eq("board_id", board_id)
    result = query.order("created_at", desc=True).limit(limit).execute()
    return result.data


def insert_raw_article(article: Dict) -> int:
    """插入原始文章"""
    sb = get_supabase()
    article["created_at"] = datetime.now().isoformat()
    result = sb.table("raw_articles").insert(article).execute()
    return result.data[0]["id"] if result.data else 0


def get_crawl_logs(board_id: str = None, limit: int = 20) -> List[Dict]:
    """获取爬取日志"""
    sb = get_supabase()
    query = sb.table("crawl_logs").select("*")
    if board_id:
        query = query.eq("board_id", board_id)
    result = query.order("timestamp", desc=True).limit(limit).execute()
    return result.data


def insert_crawl_log(log: Dict) -> int:
    """插入爬取日志"""
    sb = get_supabase()
    log["timestamp"] = datetime.now().isoformat()
    result = sb.table("crawl_logs").insert(log).execute()
    return result.data[0]["id"] if result.data else 0


def update_article(article_id: int, **kwargs):
    """更新文章"""
    sb = get_supabase()
    sb.table("raw_articles").update(kwargs).eq("id", article_id).execute()


def delete_article(article_id: int):
    """删除文章"""
    sb = get_supabase()
    sb.table("raw_articles").delete().eq("id", article_id).execute()


def get_global_last_updated() -> str:
    """获取全局最后更新时间"""
    sb = get_supabase()
    result = sb.table("crawl_logs").select("timestamp").order("timestamp", desc=True).limit(1).execute()
    if result.data:
        return result.data[0].get("timestamp", "")
    return ""


def get_board(board_id: str) -> Optional[Dict]:
    """获取板块信息"""
    sb = get_supabase()
    result = sb.table("boards").select("*").eq("id", board_id).execute()
    return result.data[0] if result.data else None


def list_boards() -> List[Dict]:
    """获取所有板块"""
    sb = get_supabase()
    result = sb.table("boards").select("*").order("sort_order").execute()
    return result.data


def update_board_status(board_id: str, **kwargs):
    """更新板块状态"""
    sb = get_supabase()
    kwargs["updated_at"] = datetime.now().isoformat()
    sb.table("boards").update(kwargs).eq("id", board_id).execute()


def get_board_status(board_id: str) -> Optional[Dict]:
    """获取板块状态"""
    sb = get_supabase()
    result = sb.table("boards").select("*").eq("id", board_id).execute()
    return result.data[0] if result.data else None

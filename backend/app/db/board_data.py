"""
各板块数据查询 — 全部 get_* 函数（按板块划分）
"""
from datetime import datetime
from typing import Optional, List, Dict
from app.db.client import get_supabase
from app.db.board_ops import get_board_meta


# ========================================================================
# 1. 运载火箭 (rocket)
# ========================================================================

def get_rocket_companies() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("rocket_companies").select("*").execute()
    return result.data


def get_rocket_timeline() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("rocket_timeline").select("*").execute()
    return result.data


def get_rocket_intro() -> Optional[Dict]:
    """返回火箭板块 AI 动态引言"""
    sb = get_supabase()
    result = sb.table("board_status").select("rocket_intro").eq("board_id", "rocket").execute()
    if result.data:
        return {"intro": result.data[0].get("rocket_intro", "")}
    return None


def set_rocket_intro(intro: str):
    sb = get_supabase()
    sb.table("board_status").update({"rocket_intro": intro}).eq("board_id", "rocket").execute()


def sync_launch_api_to_timeline():
    """手动同步 Launch API 数据到 rocket_timeline 表"""
    return 0


def sync_rocket_companies():
    """手动同步 LL2 API 数据到 rocket_companies 表"""
    return 0


def get_launch_timeline(limit: int = 50) -> List[Dict]:
    """获取发射时间线（动态计算 color/badge/done）"""
    sb = get_supabase()
    result = sb.table("rocket_launch_timeline").select("*").order("launch_time", desc=False).limit(limit).execute()

    for item in result.data:
        # color: 根据 outcome 计算
        outcome = item.get("outcome", "")
        if outcome in ("成功", "部分成功"):
            item["color"] = "green"
        elif outcome == "失败":
            item["color"] = "red"
        elif outcome == "计划中":
            item["color"] = "blue"
        else:
            item["color"] = "gray"

        # badge: 根据 rocket_id 计算
        rocket_id = item.get("rocket_id", "")
        if rocket_id in ("falcon9", "starship", "newglenn", "electron", "terran_r", "nova"):
            item["badge"] = "民营"
        elif rocket_id and (rocket_id.startswith("longmarch") or rocket_id.startswith("cz-")):
            item["badge"] = "国家队"
        else:
            item["badge"] = "国际"

        # done: 根据 outcome 计算
        item["done"] = outcome in ("成功", "部分成功")

        # 兼容前端字段名
        item["date"] = item.get("launch_time", "")
        item["title"] = item.get("mission_name", "")
        item["desc"] = item.get("brief_desc", "")

    return result.data


def upsert_launch_timeline(item: Dict) -> bool:
    """写入/更新发射时间线（rocket_launch_timeline 表）"""
    sb = get_supabase()
    timeline_id = item.get("timeline_id")
    if not timeline_id:
        return False

    existing = sb.table("rocket_launch_timeline").select("timeline_id").eq("timeline_id", timeline_id).execute()
    if existing.data:
        update_data = {k: v for k, v in item.items() if k != "timeline_id"}
        update_data["update_time"] = datetime.now().isoformat()
        sb.table("rocket_launch_timeline").update(update_data).eq("timeline_id", timeline_id).execute()
    else:
        sb.table("rocket_launch_timeline").insert(item).execute()
    return True


# ========================================================================
# 2. 中美登月 (moon)
# ========================================================================

def get_moon_highlights() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("moon_highlights").select("*").execute()
    return result.data


def get_moon_comparison() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("moon_comparison").select("*").execute()
    return result.data


# ========================================================================
# 3. 中国半导体 (semiconductor)
# ========================================================================

def get_semiconductor_highlights() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("semiconductor_highlights").select("*").execute()
    return result.data


def get_semiconductor_tab_highlights() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("semiconductor_tab_highlights").select("*").execute()
    return result.data


def get_semiconductor_tab_progress() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("semiconductor_tab_progress").select("*").execute()
    return result.data


def get_semiconductor_technologies() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("semiconductor_technologies").select("*").execute()
    return result.data


def get_semiconductor_timeline() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("semiconductor_timeline").select("*").execute()
    return result.data


# ========================================================================
# 4. 中国科技AI (china-tech)
# ========================================================================

def get_china_tech_highlights() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("china_tech_highlights").select("*").execute()
    return result.data


def get_china_tech_llm() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("china_tech_llm").select("*").execute()
    return result.data


def get_china_tech_timeline() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("china_tech_timeline").select("*").execute()
    return result.data


# ========================================================================
# 5. 中国大工程 (mega-projects)
# ========================================================================

def get_mega_projects() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("mega_projects").select("*").execute()
    return result.data


def get_mega_project_highlights() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("mega_project_highlights").select("*").execute()
    return result.data


def get_mega_project_milestones() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("mega_project_milestones").select("*").execute()
    return result.data


# ========================================================================
# 6. 可控核聚变 (fusion)
# ========================================================================

def get_fusion_highlights() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("fusion_highlights").select("*").execute()
    return result.data


def get_fusion_timeline() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("fusion_timeline").select("*").execute()
    return result.data


# ========================================================================
# 7. 科技资本 (finance)
# ========================================================================

def get_finance_grids() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("finance_grids").select("*").execute()
    return result.data


def get_finance_highlights() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("finance_highlights").select("*").execute()
    return result.data


def get_finance_sections() -> List[Dict]:
    sb = get_supabase()
    result = sb.table("finance_sections").select("*").execute()
    return result.data


# ========================================================================
# 同步 / 重同步
# ========================================================================

def re_sync_all_from_json():
    pass


def re_sync_board_from_json(board_id: str):
    pass


def get_cursor():
    return None


def _list(data):
    return data if isinstance(data, list) else []


# ========================================================================
# 完整板块数据
# ========================================================================

def get_board_full(board_id: str) -> Optional[Dict]:
    """获取板块完整数据（匹配 JSON 文件结构）"""
    meta = get_board_meta(board_id)
    if not meta:
        return None

    result = {"meta": meta}

    if board_id == "rocket":
        result["comparison_table"] = get_rocket_companies()
        timeline = get_rocket_timeline()
        result["timeline_h2"] = [t for t in timeline if t.get("period") == "h2"]
        result["timeline_2027"] = [t for t in timeline if t.get("period") == "2027"]

    elif board_id == "moon":
        result["highlights"] = get_moon_highlights()
        result["comparison"] = get_moon_comparison()

    elif board_id == "semiconductor":
        result["highlights"] = get_semiconductor_highlights()
        tab_highlights = get_semiconductor_tab_highlights()
        tab_progress = get_semiconductor_tab_progress()
        tabs = {}
        for h in tab_highlights:
            tid = h.get("tab_id", "")
            if tid not in tabs:
                tabs[tid] = {"highlights": [], "progress": []}
            tabs[tid]["highlights"].append(h)
        for p in tab_progress:
            tid = p.get("tab_id", "")
            if tid not in tabs:
                tabs[tid] = {"highlights": [], "progress": []}
            tabs[tid]["progress"].append(p)
        result["tabs"] = tabs

    elif board_id == "china-tech":
        result["highlights"] = get_china_tech_highlights()
        result["llm_table"] = get_china_tech_llm()

    elif board_id == "mega-projects":
        result["highlights"] = get_mega_project_highlights()
        projects = get_mega_projects()
        milestones = get_mega_project_milestones()
        tabs = {}
        for proj in projects:
            tid = proj.get("tab_id", "")
            if tid not in tabs:
                tabs[tid] = []
            proj_id = proj.get("id")
            proj["milestones"] = [m for m in milestones if m.get("project_id") == proj_id]
            tabs[tid].append(proj)
        result["timeline"] = tabs

    elif board_id == "fusion":
        result["highlights"] = get_fusion_highlights()
        result["timeline"] = get_fusion_timeline()

    elif board_id == "finance":
        result["fed_highlights"] = [h for h in get_finance_highlights() if h.get("section") == "fed_highlights"]
        result["fx_highlights"] = [h for h in get_finance_highlights() if h.get("section") == "fx_highlights"]
        result["spacex_highlights"] = [h for h in get_finance_highlights() if h.get("section") == "spacex_highlights"]
        result["ai_highlights"] = [h for h in get_finance_highlights() if h.get("section") == "ai_highlights"]

        sections = get_finance_sections()
        grids = get_finance_grids()
        for sec in sections:
            sec_key = sec.get("section", "")
            sec_grids = [g for g in grids if g.get("section") == sec_key]
            result[sec_key] = {
                "tag": sec.get("tag", ""),
                "name": sec.get("name", ""),
                "en": sec.get("en", ""),
                "desc": sec.get("description", ""),
                "grid": [{"k": g.get("key", ""), "v": g.get("value", "")} for g in sec_grids]
            }

    return result

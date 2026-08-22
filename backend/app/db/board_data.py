"""
各板块数据查询 — 全部 get_* 函数（按板块划分）
"""
import re
from datetime import datetime
from typing import Optional, List, Dict
from app.db.client import get_supabase
from app.db.board_ops import get_board_meta


# ========================================================================
# 1. 运载火箭 (rocket)
# ========================================================================

# 中文火箭型号正则（用于跨源查重：LL2 与航天官网对同一发射的型号表达不同，
# 提取型号核心词做"同一天 + 型号互相包含"匹配）
_ROCKET_CORE_RE = re.compile(
    r"(长征[一二三四五六七八九十百零]+号[\w甲乙丙丁]*"
    r"|朱雀[一二三]号[\w甲乙丙丁]*"
    r"|智神星[一二]号|双曲线[一二三]号|引力[一二]号"
    r"|谷神星[一二]号|天龙[二三]号|快舟[\w]*|力箭[一二]号|元行者[一二]号)"
)


def _rocket_core(mission_name: str) -> Optional[str]:
    """从任务名提取中文火箭型号核心词；非中文型号返回 None（不启用跨源查重，避免误伤同天多次发射）"""
    if not mission_name:
        return None
    m = _ROCKET_CORE_RE.search(mission_name)
    return m.group(1) if m else None


def _normalize_launch_field(value: object) -> str:
    return str(value or "").strip()


def _launch_dedup_key(launch_time: str, mission_name: str, launch_site: str) -> str:
    """同一天 + 同一任务名 + 同一发射场 → 视为同一发射（用于国际源重复写入去重）"""
    return "|".join([
        _normalize_launch_field(launch_time),
        _normalize_launch_field(mission_name),
        _normalize_launch_field(launch_site),
    ])


def _find_duplicate_launch_timeline_id(sb, item: Dict) -> Optional[str]:
    """查找与 item 语义重复的时间线条目，返回应更新的 timeline_id。"""
    launch_time = _normalize_launch_field(item.get("launch_time"))
    mission_name = _normalize_launch_field(item.get("mission_name"))
    if not launch_time or not mission_name:
        return None

    same_day = sb.table("rocket_launch_timeline").select("*").eq("launch_time", launch_time).execute()
    rows = same_day.data or []
    if not rows:
        return None

    incoming_key = _launch_dedup_key(launch_time, mission_name, item.get("launch_site", ""))
    incoming_core = _rocket_core(mission_name)

    for row in rows:
        row_id = row.get("timeline_id")
        if row_id == item.get("timeline_id"):
            continue

        row_name = _normalize_launch_field(row.get("mission_name"))
        row_key = _launch_dedup_key(
            launch_time,
            row_name,
            row.get("launch_site", ""),
        )
        if row_key == incoming_key:
            return row_id

        if incoming_core:
            row_core = _rocket_core(row_name)
            if row_core and (incoming_core in row_core or row_core in incoming_core):
                return row_id

    return None


def _dedupe_launch_timeline_rows(rows: List[Dict]) -> List[Dict]:
    """读取侧去重：同一发射只保留最近更新的一条（兼容历史重复数据）。"""
    best: Dict[str, Dict] = {}
    for row in rows:
        key = _launch_dedup_key(
            row.get("launch_time", ""),
            row.get("mission_name", ""),
            row.get("launch_site", ""),
        )
        prev = best.get(key)
        if not prev:
            best[key] = row
            continue
        prev_ts = prev.get("update_time") or prev.get("create_time") or ""
        row_ts = row.get("update_time") or row.get("create_time") or ""
        if row_ts >= prev_ts:
            best[key] = row
    deduped = list(best.values())
    deduped.sort(key=lambda r: r.get("launch_time") or "")
    return deduped


def _is_starlink_group_mission(item: Dict) -> bool:
    """猎鹰9 星链 Group 批量组网任务（信息量低，前端不展示）。"""
    parts = [
        item.get("mission_name", ""),
        item.get("payload", ""),
        item.get("title", ""),
    ]
    blob = " ".join(str(p) for p in parts).lower()
    if "starlink group" in blob:
        return True
    return "星链组网" in " ".join(str(p) for p in parts)


def _display_brief_desc(item: Dict) -> str:
    """返回前端展示用描述；旧数据若与标题重复，改为「发射场 · 结果」。"""
    title = _normalize_launch_field(item.get("mission_name"))
    desc = _normalize_launch_field(item.get("brief_desc"))
    site = _normalize_launch_field(item.get("launch_site"))
    outcome = _normalize_launch_field(item.get("outcome"))

    if desc and title:
        compact_title = title.replace(" · ", "").replace(" ", "")
        compact_desc = desc.replace(" · ", "").replace(" 执行 ", "").replace(" ", "")
        if compact_desc == compact_title or compact_desc in compact_title or compact_title in compact_desc:
            parts = [p for p in (site, outcome) if p]
            if parts:
                return " · ".join(parts)

    if desc:
        return desc
    parts = [p for p in (site, outcome) if p]
    return " · ".join(parts) if parts else title


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


def get_rocket_next_intro() -> Optional[str]:
    """获取火箭发射计划页「下一次发射评价」引言"""
    sb = get_supabase()
    result = sb.table("board_status").select("rocket_next_intro").eq("board_id", "rocket").execute()
    if result.data:
        return result.data[0].get("rocket_next_intro", "") or None
    return None


def set_rocket_next_intro(intro: str):
    """写入火箭发射计划页「下一次发射评价」引言"""
    sb = get_supabase()
    sb.table("board_status").update({"rocket_next_intro": intro}).eq("board_id", "rocket").execute()


def get_rocket_last_review() -> Optional[str]:
    """获取火箭发射计划页「最近一期发射总结」"""
    sb = get_supabase()
    result = sb.table("board_status").select("rocket_last_review").eq("board_id", "rocket").execute()
    if result.data:
        return result.data[0].get("rocket_last_review", "") or None
    return None


def set_rocket_last_review(review: str):
    """写入火箭发射计划页「最近一期发射总结」"""
    sb = get_supabase()
    sb.table("board_status").update({"rocket_last_review": review}).eq("board_id", "rocket").execute()


def get_rocket_ai_last_done_key() -> Optional[str]:
    """获取最近一次 AI 改写已处理过的「最后一条已完成发射」标记"""
    sb = get_supabase()
    result = sb.table("board_status").select("rocket_ai_last_done_key").eq("board_id", "rocket").execute()
    if result.data:
        return result.data[0].get("rocket_ai_last_done_key", "") or None
    return None


def set_rocket_ai_last_done_key(key: str):
    """记录最近一次 AI 改写已处理过的「最后一条已完成发射」标记"""
    sb = get_supabase()
    sb.table("board_status").update({"rocket_ai_last_done_key": key}).eq("board_id", "rocket").execute()


def get_launch_timeline(limit: int = 50) -> List[Dict]:
    """获取发射时间线（动态计算 color/badge/done）"""
    sb = get_supabase()
    # 星链组网任务占比高，多拉取一些再过滤
    fetch_limit = max(limit * 8, 200)
    result = sb.table("rocket_launch_timeline").select("*").order("launch_time", desc=False).limit(fetch_limit).execute()
    rows = [
        row for row in _dedupe_launch_timeline_rows(result.data or [])
        if not _is_starlink_group_mission(row)
    ][:limit]

    for item in rows:
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
        item["desc"] = _display_brief_desc(item)

    return rows


def upsert_launch_timeline(item: Dict) -> bool:
    """写入/更新发射时间线（rocket_launch_timeline 表）

    去重顺序：
    1. 按 timeline_id（同源唯一键）— 存在则更新
    2. 跨源查重：同一天 +（任务名+发射场完全一致，或中文型号核心词互相包含）→ 更新该行
    3. 均未命中 → 插入新行
    """
    sb = get_supabase()
    timeline_id = item.get("timeline_id")
    if not timeline_id:
        return False

    existing = sb.table("rocket_launch_timeline").select("timeline_id").eq("timeline_id", timeline_id).execute()
    if existing.data:
        update_data = {k: v for k, v in item.items() if k != "timeline_id"}
        update_data["update_time"] = datetime.now().isoformat()
        sb.table("rocket_launch_timeline").update(update_data).eq("timeline_id", timeline_id).execute()
        return True

    duplicate_id = _find_duplicate_launch_timeline_id(sb, item)
    if duplicate_id:
        update_data = {k: v for k, v in item.items() if k != "timeline_id"}
        update_data["update_time"] = datetime.now().isoformat()
        sb.table("rocket_launch_timeline").update(update_data).eq("timeline_id", duplicate_id).execute()
        return True

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
# 5. 中国超级工程 (mega-projects)
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
    """从 data/*.json 同步全部 7 个版块到数据库（幂等，单版块失败不影响其他）"""
    from app.db.json_sync import sync_all_from_json
    return sync_all_from_json()


def re_sync_board_from_json(board_id: str):
    """从 data/{board_id}.json 同步单个版块到数据库（幂等，先查后插/更新）"""
    from app.db.json_sync import sync_board_from_json
    return sync_board_from_json(board_id)


def get_cursor():
    return None


def _list(data):
    return data if isinstance(data, list) else []


# ========================================================================
# 完整板块数据
# ========================================================================

def _normalize_hl(row: Dict) -> Dict:
    """DB 高亮行 → 前端字段（label→lbl），保持 JSON 结构一致"""
    return {"num": row.get("num", ""), "lbl": row.get("label") or row.get("lbl") or "", "color": row.get("color", "")}


def _normalize_progress(row: Dict) -> Dict:
    """DB 进度行 → 前端字段（year→yr / value→val）"""
    return {
        "yr": row.get("year") or row.get("yr") or "",
        "val": row.get("value") or row.get("val") or "",
        "lbl": row.get("label") or row.get("lbl") or "",
        "cls": row.get("cls") or "",
    }


def _build_semiconductor_payload() -> Dict:
    """组装半导体精简数据（高亮 + 各子 Tab 高亮/进度），供并入 china-tech"""
    hl = [_normalize_hl(h) for h in get_semiconductor_highlights()]
    tab_highlights = get_semiconductor_tab_highlights()
    tab_progress = get_semiconductor_tab_progress()
    tabs = {}
    for h in tab_highlights:
        tid = h.get("tab_id", "")
        tabs.setdefault(tid, {"highlights": [], "progress": []})
        tabs[tid]["highlights"].append(_normalize_hl(h))
    for p in tab_progress:
        tid = p.get("tab_id", "")
        tabs.setdefault(tid, {"highlights": [], "progress": []})
        tabs[tid]["progress"].append(_normalize_progress(p))
    return {"highlights": hl, "tabs": tabs}


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
        # 半导体板块已并入中国科技：作为子数据提供，供 china-tech 页「半导体」Tab 渲染
        result["semiconductor"] = _build_semiconductor_payload()

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

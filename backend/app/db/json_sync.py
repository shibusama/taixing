# -*- coding: utf-8 -*-
"""
data/*.json → 数据库 幂等同步（双模式：Supabase / 本地 SQLite 适配层）

由 board_data.re_sync_board_from_json / re_sync_all_from_json 调用。
所有写入均通过 `from app.db.client import get_db_mode, get_supabase` 取得的
supabase 兼容链式客户端完成：
    .table().select().eq().limit().update().insert().execute()

幂等策略：按各表唯一键「先查后插」——
  * 已存在 → update（仅更新 JSON 中出现的字段，不覆盖缺失字段）
  * 不存在且主键可自增（identity/serial）→ insert
  * 不存在但主键为 integer 且无默认值（JSON 无 id）→ 跳过并报告，
    绝不猜测 id（避免与现有行主键冲突）
  * 本地 SQLite 模式例外：id 列为 INTEGER PRIMARY KEY 时由 SQLite 自动生成，
    允许插入新行（Supabase 模式保持跳过）
不删除任何现有数据；数据库未配置/表缺失/字段缺失均捕获异常并记入 skipped。
"""
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.db.client import get_db_mode, get_supabase

# 七大版块（与 data/*.json 文件名一一对应）
BOARDS: List[str] = [
    "rocket", "moon", "semiconductor", "china-tech",
    "mega-projects", "fusion", "finance",
]

DATA_DIR: Path = Path(__file__).resolve().parents[3] / "data"

# ---------------------------------------------------------------------------
# 字段映射（JSON 字段 → DB 列名；第三个元素为可选转换器）
# ---------------------------------------------------------------------------

def _json_text(v: Any) -> str:
    """list/dict → JSON 字符串（如 china_tech_llm.hi_fields）"""
    return json.dumps(v, ensure_ascii=False)

# highlights 通用映射（num/lbl/color）
HIGHLIGHT_MAP: List[Tuple[str, str]] = [("num", "num"), ("lbl", "label"), ("color", "color")]

ROCKET_COMPANY_MAP: List[Tuple[str, str]] = [
    ("rocket", "rocket"), ("company", "company"), ("country", "country"),
    ("fuel", "fuel"), ("diameter", "diameter"), ("thrust", "thrust"),
    ("leo", "leo"), ("recovery", "recovery"), ("status", "status"),
    ("key", "key"),
]

MOON_COMPARISON_MAP: List[Tuple[str, str]] = [
    ("dim", "aspect"), ("china", "china_value"), ("us", "usa_value"),
]

LLM_MAP: List[Tuple[str, str]] = [
    ("model", "model"), ("company", "company"), ("params", "params"),
    ("ctx", "context_window"), ("coding", "coding"), ("math", "math"),
    ("arena", "arena"), ("opensource", "opensource"), ("price", "price"),
    ("hi_fields", "hi_fields", _json_text),
]

MEGA_PROJECT_MAP: List[Tuple[str, str]] = [
    ("tab", "tab_id"), ("emoji", "emoji"), ("name", "project_name"),
    ("target", "target_id"), ("status", "status"), ("statusClass", "status_class"),
]

MEGA_MILESTONE_MAP: List[Tuple[str, str]] = [
    ("marker", "marker"), ("date", "event_date"), ("badge", "badge"),
    ("badgeClass", "badge_class"), ("title", "title"),
]

FINANCE_HIGHLIGHT_MAP: List[Tuple[str, str]] = [
    ("label", "label"), ("num", "num"), ("sub", "sub"), ("color", "color"),
]

FINANCE_SECTION_MAP: List[Tuple[str, str]] = [
    ("tag", "tag"), ("name", "name"), ("en", "en"), ("desc", "description"),
]

FUSION_TIMELINE_MAP: List[Tuple[str, str]] = [
    ("date", "event_date"), ("title", "title"),
    ("desc", "description"), ("color", "color"),
]

# finance.json 的 highlights 分组 key 与 sections 分组 key
FINANCE_HIGHLIGHT_KEYS: Tuple[str, ...] = (
    "fed_highlights", "fx_highlights", "spacex_highlights", "ai_highlights",
)
FINANCE_SECTION_KEYS: Tuple[str, ...] = (
    "fed_schedule", "fed_officials", "fx_rates", "fx_cb_rates",
    "spacex_finance", "spacex_breakdown", "spacex_analyst",
    "ai_anthropic", "ai_openai", "ai_comparison",
)

# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------

def _map_row(item: Dict, mapping: List[Tuple[str, str]]) -> Dict:
    """按 mapping 提取字段；仅保留 JSON 中实际出现的字段。"""
    row: Dict[str, Any] = {}
    for spec in mapping:
        src, dst = spec[0], spec[1]
        conv: Optional[Callable[[Any], Any]] = spec[2] if len(spec) > 2 else None
        if src in item and item[src] is not None:
            row[dst] = conv(item[src]) if conv else item[src]
    return row


def _load_payload(board_id: str) -> Optional[Dict]:
    path = DATA_DIR / f"{board_id}.json"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else None


def _is_local_mode() -> bool:
    """当前是否为本地 SQLite 模式（未配置 Supabase 环境变量时自动降级）"""
    try:
        return get_db_mode() == "local"
    except Exception:
        return False


def _local_id_auto(table: str) -> bool:
    """本地 SQLite 模式：id 列为 INTEGER PRIMARY KEY 时可由数据库自动生成（无需提供 id）"""
    try:
        from app.db.local import schema as local_schema
        for name, typ, constraints, _flags in local_schema.TABLES.get(table, []):
            if name == "id":
                return typ == "INTEGER" and "PRIMARY KEY" in (constraints or "").upper()
    except Exception:
        pass
    return False


def _select_one(sb, table: str, keys: Dict[str, Any]) -> Optional[Dict]:
    q = sb.table(table).select("*")
    for k, v in keys.items():
        q = q.eq(k, v)
    q = q.limit(1)
    result = q.execute()
    return (result.data or [None])[0]


def _sync_meta(sb, board_id: str, meta: Dict, skipped: List[str]) -> int:
    """board_meta upsert（主键 board_id，直接给值，无需自增 id）"""
    row: Dict[str, Any] = {"board_id": board_id}
    for k in ("updated", "source", "module"):
        if k in meta and meta[k] is not None:
            row[k] = str(meta[k])
    try:
        existing = _select_one(sb, "board_meta", {"board_id": board_id})
        if existing:
            update_data = {k: v for k, v in row.items() if k != "board_id"}
            if update_data:
                sb.table("board_meta").update(update_data).eq("board_id", board_id).execute()
        else:
            sb.table("board_meta").insert(row).execute()
        return 1
    except Exception as e:
        skipped.append(f"{board_id}: board_meta 写入失败（{e}）")
        return 0


def _sync_table(
    sb,
    table: str,
    rows: List[Dict],
    key_cols: List[str],
    sort_order: str = "int",   # "int" | "str" | None
    auto_id: bool = True,      # 主键是否可由数据库自增
    skipped: Optional[List[str]] = None,
) -> int:
    """幂等 upsert：按 key_cols 先查后插/更新。返回写入条数（insert + update）。"""
    if skipped is None:
        skipped = []
    if not rows:
        return 0

    written = 0
    missing_id = 0
    can_insert = auto_id or (_is_local_mode() and _local_id_auto(table))
    try:
        for idx, row in enumerate(rows):
            if sort_order:
                row["sort_order"] = str(idx) if sort_order == "str" else idx

            keys = {k: row.get(k) for k in key_cols}
            if not all(keys.values()):
                skipped.append(f"{table}: 第 {idx} 行缺少唯一键 {key_cols}，跳过")
                continue

            existing = _select_one(sb, table, keys)
            if existing:
                update_data = {k: v for k, v in row.items() if k not in key_cols}
                if update_data:
                    q = sb.table(table).update(update_data)
                    for k, v in keys.items():
                        q = q.eq(k, v)
                    q.execute()
                written += 1
            elif can_insert:
                sb.table(table).insert(row).execute()
                written += 1
            else:
                missing_id += 1
    except Exception as e:
        skipped.append(f"{table}: 同步失败，已中止该表（{e}）")
        return written

    if missing_id:
        skipped.append(
            f"{table}: 主键 id 为 integer 且无默认值、JSON 无 id，无法安全插入 {missing_id} 条"
            "（已存在的行已更新；不猜测 id 以避免主键冲突）"
        )
    return written


# ---------------------------------------------------------------------------
# 各版块同步
# ---------------------------------------------------------------------------

def _sync_rocket(sb, payload: Dict, skipped: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    counts["board_meta"] = _sync_meta(sb, "rocket", payload.get("meta") or {}, skipped)

    companies = [
        _map_row(i, ROCKET_COMPANY_MAP)
        for i in (payload.get("comparison_table") or [])
        if isinstance(i, dict)
    ]
    counts["rocket_companies"] = _sync_table(
        sb, "rocket_companies", companies, ["key"], sort_order="str",
        auto_id=False, skipped=skipped,
    )

    # rocket 时间线：timeline_h2/timeline_2027 → rocket_timeline 表（period 区分 h2/2027），
    # 字段与 get_board_full/get_rocket_timeline 读取逻辑对齐（date/title/desc/color/badge/done）
    rt_rows: List[Dict] = []
    for period, key in (("h2", "timeline_h2"), ("2027", "timeline_2027")):
        for it in (payload.get(key) or []):
            if isinstance(it, dict):
                row = {f: it[f] for f in ("date", "title", "desc", "color", "badge", "done")
                       if f in it and it[f] is not None}
                row["period"] = period
                rt_rows.append(row)

    if rt_rows:
        if _is_local_mode():
            counts["rocket_timeline"] = _sync_table(
                sb, "rocket_timeline", rt_rows, ["period", "date", "title"],
                sort_order="int", auto_id=True, skipped=skipped,
            )
        else:
            skipped.append(
                "rocket: timeline_h2/timeline_2027 对应 rocket_timeline 表（本地 SQLite 模式表，"
                "schema.ts/Supabase 无此表），Supabase 模式跳过"
            )
    return counts


def _sync_moon(sb, payload: Dict, skipped: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    counts["board_meta"] = _sync_meta(sb, "moon", payload.get("meta") or {}, skipped)

    highlights = [
        _map_row(i, HIGHLIGHT_MAP)
        for i in (payload.get("highlights") or [])
        if isinstance(i, dict)
    ]
    counts["moon_highlights"] = _sync_table(
        sb, "moon_highlights", highlights, ["num", "label"], sort_order="str",
        auto_id=False, skipped=skipped,
    )

    comparison = [
        _map_row(i, MOON_COMPARISON_MAP)
        for i in (payload.get("comparison") or [])
        if isinstance(i, dict)
    ]
    counts["moon_comparison"] = _sync_table(
        sb, "moon_comparison", comparison, ["aspect"], sort_order=None,
        auto_id=True, skipped=skipped,
    )
    return counts


def _sync_semiconductor(sb, payload: Dict, skipped: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    counts["board_meta"] = _sync_meta(sb, "semiconductor", payload.get("meta") or {}, skipped)

    highlights = [
        _map_row(i, HIGHLIGHT_MAP)
        for i in (payload.get("highlights") or [])
        if isinstance(i, dict)
    ]
    counts["semiconductor_highlights"] = _sync_table(
        sb, "semiconductor_highlights", highlights, ["num", "label"],
        sort_order="int", auto_id=True, skipped=skipped,
    )

    tab_highlights: List[Dict] = []
    tab_progress: List[Dict] = []
    tabs = payload.get("tabs") or {}
    if isinstance(tabs, dict):
        for tab_id, tab in tabs.items():
            if not isinstance(tab, dict):
                continue
            for h in (tab.get("highlights") or []):
                if isinstance(h, dict):
                    row = _map_row(h, HIGHLIGHT_MAP)
                    row["tab_id"] = tab_id
                    tab_highlights.append(row)
            for p in (tab.get("progress") or []):
                if isinstance(p, dict):
                    row = _map_row(p, [("yr", "year"), ("val", "value"), ("lbl", "label"), ("cls", "cls")])
                    row["tab_id"] = tab_id
                    tab_progress.append(row)

    counts["semiconductor_tab_highlights"] = _sync_table(
        sb, "semiconductor_tab_highlights", tab_highlights, ["tab_id", "num", "label"],
        sort_order="int", auto_id=True, skipped=skipped,
    )
    counts["semiconductor_tab_progress"] = _sync_table(
        sb, "semiconductor_tab_progress", tab_progress, ["tab_id", "year", "label"],
        sort_order="int", auto_id=True, skipped=skipped,
    )
    return counts


def _sync_china_tech(sb, payload: Dict, skipped: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    counts["board_meta"] = _sync_meta(sb, "china-tech", payload.get("meta") or {}, skipped)

    highlights = [
        _map_row(i, HIGHLIGHT_MAP)
        for i in (payload.get("highlights") or [])
        if isinstance(i, dict)
    ]
    counts["china_tech_highlights"] = _sync_table(
        sb, "china_tech_highlights", highlights, ["num", "label"],
        sort_order="int", auto_id=True, skipped=skipped,
    )

    llm_rows = [
        _map_row(i, LLM_MAP)
        for i in (payload.get("llm_table") or [])
        if isinstance(i, dict)
    ]
    counts["china_tech_llm"] = _sync_table(
        sb, "china_tech_llm", llm_rows, ["model", "company"],
        sort_order="int", auto_id=True, skipped=skipped,
    )
    return counts


def _sync_mega_projects(sb, payload: Dict, skipped: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    counts["board_meta"] = _sync_meta(sb, "mega-projects", payload.get("meta") or {}, skipped)

    highlights = [
        _map_row(i, HIGHLIGHT_MAP)
        for i in (payload.get("highlights") or [])
        if isinstance(i, dict)
    ]
    counts["mega_project_highlights"] = _sync_table(
        sb, "mega_project_highlights", highlights, ["num", "label"],
        sort_order="int", auto_id=True, skipped=skipped,
    )

    projects: List[Dict] = []
    has_milestones = False
    timeline = payload.get("timeline") or []
    if isinstance(timeline, list):
        for proj in timeline:
            if not isinstance(proj, dict):
                continue
            row = _map_row(proj, MEGA_PROJECT_MAP)
            projects.append(row)
            if proj.get("items"):
                has_milestones = True

    counts["mega_projects"] = _sync_table(
        sb, "mega_projects", projects, ["target_id"], sort_order="str",
        auto_id=False, skipped=skipped,
    )
    if has_milestones:
        if _is_local_mode():
            # 本地模式：mega_projects.id 由 SQLite 自动生成，插入后按 target_id 查父表拿到 id，
            # 再灌入里程碑（project_id 外键不悬空）
            m_rows: List[Dict] = []
            for proj in timeline:
                if not isinstance(proj, dict):
                    continue
                target_id = proj.get("target")
                if not target_id:
                    continue
                parent = _select_one(sb, "mega_projects", {"target_id": target_id})
                if not parent or not parent.get("id"):
                    continue
                for it in (proj.get("items") or []):
                    if isinstance(it, dict):
                        row = _map_row(it, MEGA_MILESTONE_MAP)
                        row["project_id"] = parent["id"]
                        m_rows.append(row)
            counts["mega_project_milestones"] = _sync_table(
                sb, "mega_project_milestones", m_rows, ["project_id", "event_date", "title"],
                sort_order="int", auto_id=True, skipped=skipped,
            )
        else:
            skipped.append(
                "mega-projects: mega_project_milestones 跳过——milestones.project_id 依赖"
                " mega_projects.id（integer 主键无默认值、JSON 无 id），父表无法安全插入，"
                "为避免悬空引用不写入里程碑"
            )
    return counts


def _sync_fusion(sb, payload: Dict, skipped: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    counts["board_meta"] = _sync_meta(sb, "fusion", payload.get("meta") or {}, skipped)

    highlights = [
        _map_row(i, HIGHLIGHT_MAP)
        for i in (payload.get("highlights") or [])
        if isinstance(i, dict)
    ]
    counts["fusion_highlights"] = _sync_table(
        sb, "fusion_highlights", highlights, ["num", "label"],
        sort_order="int", auto_id=True, skipped=skipped,
    )

    timeline: List[Dict] = []
    tl = payload.get("timeline")
    if isinstance(tl, dict):
        for region, group in tl.items():
            if not isinstance(group, dict):
                continue
            label = group.get("label")
            for it in (group.get("items") or []):
                if isinstance(it, dict):
                    row = _map_row(it, FUSION_TIMELINE_MAP)
                    row["region"] = region
                    if label is not None:
                        row["region_label"] = label
                    timeline.append(row)

    counts["fusion_timeline"] = _sync_table(
        sb, "fusion_timeline", timeline, ["region", "event_date", "title"],
        sort_order="str", auto_id=False, skipped=skipped,
    )
    return counts


def _sync_finance(sb, payload: Dict, skipped: List[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    counts["board_meta"] = _sync_meta(sb, "finance", payload.get("meta") or {}, skipped)

    # highlights：按 JSON key 分组 → finance_highlights.section
    fh_rows: List[Dict] = []
    for section in FINANCE_HIGHLIGHT_KEYS:
        for item in (payload.get(section) or []):
            if isinstance(item, dict):
                row = _map_row(item, FINANCE_HIGHLIGHT_MAP)
                row["section"] = section
                fh_rows.append(row)
    counts["finance_highlights"] = _sync_table(
        sb, "finance_highlights", fh_rows, ["section", "label"],
        sort_order="int", auto_id=True, skipped=skipped,
    )

    # sections + grids
    sec_rows: List[Dict] = []
    grid_rows: List[Dict] = []
    for section in FINANCE_SECTION_KEYS:
        block = payload.get(section)
        if not isinstance(block, dict):
            continue
        sec_row = _map_row(block, FINANCE_SECTION_MAP)
        sec_row["section"] = section
        sec_rows.append(sec_row)
        for g in (block.get("grid") or []):
            if isinstance(g, dict):
                grid_rows.append({"section": section, "key": g.get("k"), "value": g.get("v")})

    counts["finance_sections"] = _sync_table(
        sb, "finance_sections", sec_rows, ["section"],
        sort_order="int", auto_id=True, skipped=skipped,
    )
    counts["finance_grids"] = _sync_table(
        sb, "finance_grids", grid_rows, ["section", "key"],
        sort_order="int", auto_id=True, skipped=skipped,
    )
    return counts


_BOARD_SYNCERS: Dict[str, Callable] = {
    "rocket": _sync_rocket,
    "moon": _sync_moon,
    "semiconductor": _sync_semiconductor,
    "china-tech": _sync_china_tech,
    "mega-projects": _sync_mega_projects,
    "fusion": _sync_fusion,
    "finance": _sync_finance,
}


# ---------------------------------------------------------------------------
# 公共入口
# ---------------------------------------------------------------------------

def sync_board_from_json(board_id: str, sb=None) -> Dict:
    """读 data/{board_id}.json 并幂等同步到数据库。

    返回: {"status": "ok", board_id: {表名: 写入条数}, "skipped": [原因...]}
    """
    skipped: List[str] = []
    counts: Dict[str, int] = {}

    if sb is None:
        try:
            sb = get_supabase()
        except Exception as e:
            skipped.append(f"{board_id}: 数据库未配置或客户端获取失败（{e}），跳过写入")
            return {"status": "ok", board_id: counts, "skipped": skipped}

    syncer = _BOARD_SYNCERS.get(board_id)
    if syncer is None:
        skipped.append(f"{board_id}: 未配置该版块的 JSON→DB 映射，跳过")
        return {"status": "ok", board_id: counts, "skipped": skipped}

    try:
        payload = _load_payload(board_id)
    except Exception as e:
        skipped.append(f"{board_id}: 读取 data/{board_id}.json 失败（{e}）")
        return {"status": "ok", board_id: counts, "skipped": skipped}

    if payload is None:
        skipped.append(f"{board_id}: data/{board_id}.json 顶层不是 JSON 对象，跳过")
        return {"status": "ok", board_id: counts, "skipped": skipped}

    try:
        counts = syncer(sb, payload, skipped)
    except Exception as e:
        skipped.append(f"{board_id}: 同步过程异常（{e}）")

    return {"status": "ok", board_id: counts, "skipped": skipped}


def sync_all_from_json(sb=None) -> Dict:
    """遍历 7 个版块调用单版块同步，汇总结果；单版块失败不影响其他。"""
    result: Dict = {"status": "ok", "skipped": []}
    for board_id in BOARDS:
        res = sync_board_from_json(board_id, sb=sb)
        result[board_id] = res.get(board_id, {})
        result["skipped"].extend(res.get("skipped", []))
    return result

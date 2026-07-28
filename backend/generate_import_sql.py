"""
钛星 JSON → SQL 生成脚本
读取 data/*.json 文件，生成可直接执行的 SQL INSERT 语句

用法：
  python backend/generate_import_sql.py              # 生成所有板块的 SQL
  python backend/generate_import_sql.py --board rocket  # 只生成火箭板块
  python backend/generate_import_sql.py --output import.sql  # 输出到文件
"""
import os
import sys
import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

BOARD_MAP = {
    "rocket": "rocket",
    "moon": "moon",
    "semiconductor": "semiconductor",
    "china-tech": "china-tech",
    "mega-projects": "mega-projects",
    "fusion": "fusion",
    "finance": "finance",
}


def sql_escape(s):
    """SQL 字符串转义"""
    if s is None:
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"


def generate_meta_sql(board_id: str, meta: dict) -> str:
    """生成 board_meta 的 INSERT SQL"""
    updated = sql_escape(meta.get("updated", ""))
    source = sql_escape(meta.get("source", ""))
    module = sql_escape(meta.get("module", ""))
    return f"INSERT INTO board_meta (board_id, updated, source, module) VALUES ({sql_escape(board_id)}, {updated}, {source}, {module}) ON CONFLICT (board_id) DO UPDATE SET updated = EXCLUDED.updated, source = EXCLUDED.source, module = EXCLUDED.module;"


def generate_rocket_sql(data: dict) -> str:
    """生成火箭板块的 INSERT SQL"""
    sql_parts = []

    # comparison_table → rocket_companies
    companies = data.get("comparison_table", [])
    for i, c in enumerate(companies):
        sql_parts.append(
            f"INSERT INTO rocket_companies (id, rocket, company, country, fuel, diameter, thrust, leo, recovery, status, key, sort_order) "
            f"VALUES ({i+1}, {sql_escape(c.get('rocket',''))}, {sql_escape(c.get('company',''))}, {sql_escape(c.get('country',''))}, "
            f"{sql_escape(c.get('fuel',''))}, {sql_escape(c.get('diameter',''))}, {sql_escape(c.get('thrust',''))}, "
            f"{sql_escape(c.get('leo',''))}, {sql_escape(c.get('recovery',''))}, {sql_escape(c.get('status',''))}, "
            f"{sql_escape(c.get('key',''))}, {sql_escape(str(i))}) "
            f"ON CONFLICT (id) DO UPDATE SET rocket=EXCLUDED.rocket, company=EXCLUDED.company, country=EXCLUDED.country, "
            f"fuel=EXCLUDED.fuel, diameter=EXCLUDED.diameter, thrust=EXCLUDED.thrust, leo=EXCLUDED.leo, "
            f"recovery=EXCLUDED.recovery, status=EXCLUDED.status, key=EXCLUDED.key, sort_order=EXCLUDED.sort_order;"
        )

    # timeline_h2 + timeline_2027 → rocket_timeline
    timeline_items = []
    for item in data.get("timeline_h2", []):
        timeline_items.append({
            "period": "h2",
            "event_date": item.get("date", ""),
            "title": item.get("title", ""),
            "description": item.get("desc", ""),
            "color": item.get("color", ""),
            "badge": item.get("badge", ""),
            "done": str(item.get("done", "")),
        })
    for item in data.get("timeline_2027", []):
        timeline_items.append({
            "period": "2027",
            "event_date": item.get("date", ""),
            "title": item.get("title", ""),
            "description": item.get("desc", ""),
            "color": item.get("color", ""),
            "badge": item.get("badge", ""),
            "done": "",
        })
    for i, item in enumerate(timeline_items):
        sql_parts.append(
            f"INSERT INTO rocket_timeline (id, period, event_date, title, description, color, badge, done, sort_order) "
            f"VALUES ({i+1}, {sql_escape(item['period'])}, {sql_escape(item['event_date'])}, {sql_escape(item['title'])}, "
            f"{sql_escape(item['description'])}, {sql_escape(item['color'])}, {sql_escape(item['badge'])}, "
            f"{sql_escape(item['done'])}, {sql_escape(str(i))}) "
            f"ON CONFLICT (id) DO UPDATE SET period=EXCLUDED.period, event_date=EXCLUDED.event_date, title=EXCLUDED.title, "
            f"description=EXCLUDED.description, color=EXCLUDED.color, badge=EXCLUDED.badge, done=EXCLUDED.done, sort_order=EXCLUDED.sort_order;"
        )

    return "\n".join(sql_parts)


def generate_moon_sql(data: dict) -> str:
    """生成中美登月板块的 INSERT SQL"""
    sql_parts = []

    # highlights → moon_highlights
    highlights = data.get("highlights", [])
    for i, h in enumerate(highlights):
        sql_parts.append(
            f"INSERT INTO moon_highlights (id, num, label, color, sort_order) "
            f"VALUES ({i+1}, {sql_escape(h.get('num',''))}, {sql_escape(h.get('lbl',''))}, {sql_escape(h.get('color',''))}, {sql_escape(str(i))}) "
            f"ON CONFLICT (id) DO UPDATE SET num=EXCLUDED.num, label=EXCLUDED.label, color=EXCLUDED.color, sort_order=EXCLUDED.sort_order;"
        )

    # comparison → moon_comparison
    comparisons = data.get("comparison", [])
    for i, c in enumerate(comparisons):
        sql_parts.append(
            f"INSERT INTO moon_comparison (id, aspect, china_value, usa_value, notes) "
            f"VALUES ({i+1}, {sql_escape(c.get('dim',''))}, {sql_escape(c.get('china',''))}, {sql_escape(c.get('us',''))}, {sql_escape(c.get('highlight',''))}) "
            f"ON CONFLICT (id) DO UPDATE SET aspect=EXCLUDED.aspect, china_value=EXCLUDED.china_value, usa_value=EXCLUDED.usa_value, notes=EXCLUDED.notes;"
        )

    return "\n".join(sql_parts)


def generate_semiconductor_sql(data: dict) -> str:
    """生成半导体板块的 INSERT SQL"""
    sql_parts = []

    # highlights → semiconductor_highlights
    highlights = data.get("highlights", [])
    for i, h in enumerate(highlights):
        sql_parts.append(
            f"INSERT INTO semiconductor_highlights (num, label, color, sort_order) "
            f"VALUES ({sql_escape(h.get('num',''))}, {sql_escape(h.get('lbl',''))}, {sql_escape(h.get('color',''))}, {i});"
        )

    # tabs → semiconductor_tab_highlights + semiconductor_tab_progress
    tabs = data.get("tabs", {})
    for tab_id, tab_data in tabs.items():
        tab_hls = tab_data.get("highlights", [])
        for i, h in enumerate(tab_hls):
            sql_parts.append(
                f"INSERT INTO semiconductor_tab_highlights (tab_id, num, label, color, sort_order) "
                f"VALUES ({sql_escape(tab_id)}, {sql_escape(h.get('num',''))}, {sql_escape(h.get('lbl',''))}, {sql_escape(h.get('color',''))}, {i});"
            )

        tab_progress = tab_data.get("progress", [])
        for i, p in enumerate(tab_progress):
            sql_parts.append(
                f"INSERT INTO semiconductor_tab_progress (tab_id, year, value, label, cls, sort_order) "
                f"VALUES ({sql_escape(tab_id)}, {sql_escape(p.get('yr',''))}, {sql_escape(p.get('val',''))}, {sql_escape(p.get('lbl',''))}, {sql_escape(p.get('cls',''))}, {i});"
            )

    return "\n".join(sql_parts)


def generate_china_tech_sql(data: dict) -> str:
    """生成中国科技 AI 板块的 INSERT SQL"""
    sql_parts = []

    # highlights → china_tech_highlights
    highlights = data.get("highlights", [])
    for i, h in enumerate(highlights):
        sql_parts.append(
            f"INSERT INTO china_tech_highlights (num, label, color, sort_order) "
            f"VALUES ({sql_escape(h.get('num',''))}, {sql_escape(h.get('lbl',''))}, {sql_escape(h.get('color',''))}, {i});"
        )

    # llm_table → china_tech_llm
    llm_items = data.get("llm_table", [])
    for i, item in enumerate(llm_items):
        sql_parts.append(
            f"INSERT INTO china_tech_llm (model, company, params, context_window, coding, math, arena, opensource, price, hi_fields, sort_order) "
            f"VALUES ({sql_escape(item.get('model',''))}, {sql_escape(item.get('company',''))}, {sql_escape(item.get('params',''))}, "
            f"{sql_escape(item.get('ctx',''))}, {sql_escape(item.get('coding',''))}, {sql_escape(item.get('math',''))}, "
            f"{sql_escape(item.get('arena',''))}, {sql_escape(item.get('opensource',''))}, {sql_escape(item.get('price',''))}, "
            f"{sql_escape(item.get('hi_fields',''))}, {i});"
        )

    return "\n".join(sql_parts)


def generate_mega_projects_sql(data: dict) -> str:
    """生成中国大工程板块的 INSERT SQL"""
    sql_parts = []

    # highlights → mega_project_highlights
    highlights = data.get("highlights", [])
    for i, h in enumerate(highlights):
        sql_parts.append(
            f"INSERT INTO mega_project_highlights (num, label, color, sort_order) "
            f"VALUES ({sql_escape(h.get('num',''))}, {sql_escape(h.get('lbl',''))}, {sql_escape(h.get('color',''))}, {i});"
        )

    # timeline → mega_projects + mega_project_milestones
    timeline = data.get("timeline", [])
    project_id = 0
    milestone_id = 0
    for proj in timeline:
        project_id += 1
        sql_parts.append(
            f"INSERT INTO mega_projects (id, tab_id, emoji, project_name, target_id, status, status_class, sort_order) "
            f"VALUES ({project_id}, {sql_escape(proj.get('tab',''))}, {sql_escape(proj.get('emoji',''))}, "
            f"{sql_escape(proj.get('name',''))}, {sql_escape(proj.get('target',''))}, {sql_escape(proj.get('status',''))}, "
            f"{sql_escape(proj.get('statusClass',''))}, {sql_escape(str(project_id-1))}) "
            f"ON CONFLICT (id) DO UPDATE SET tab_id=EXCLUDED.tab_id, emoji=EXCLUDED.emoji, project_name=EXCLUDED.project_name, "
            f"target_id=EXCLUDED.target_id, status=EXCLUDED.status, status_class=EXCLUDED.status_class, sort_order=EXCLUDED.sort_order;"
        )

        for item in proj.get("items", []):
            milestone_id += 1
            sql_parts.append(
                f"INSERT INTO mega_project_milestones (project_id, marker, event_date, badge, badge_class, title, sort_order) "
                f"VALUES ({project_id}, {sql_escape(item.get('marker',''))}, {sql_escape(item.get('date',''))}, "
                f"{sql_escape(item.get('badge',''))}, {sql_escape(item.get('badgeClass',''))}, {sql_escape(item.get('title',''))}, {milestone_id-1});"
            )

    return "\n".join(sql_parts)


def generate_fusion_sql(data: dict) -> str:
    """生成可控核聚变板块的 INSERT SQL"""
    sql_parts = []

    # highlights → fusion_highlights
    highlights = data.get("highlights", [])
    for i, h in enumerate(highlights):
        sql_parts.append(
            f"INSERT INTO fusion_highlights (num, label, color, sort_order) "
            f"VALUES ({sql_escape(h.get('num',''))}, {sql_escape(h.get('lbl',''))}, {sql_escape(h.get('color',''))}, {i});"
        )

    # timeline → fusion_timeline
    timeline = data.get("timeline", {})
    timeline_items = []
    sort_order = 0
    for region_key, region_data in timeline.items():
        region_label = region_data.get("label", "")
        for item in region_data.get("items", []):
            timeline_items.append({
                "region": region_key,
                "region_label": region_label,
                "event_date": item.get("date", ""),
                "title": item.get("title", ""),
                "description": item.get("desc", ""),
                "color": item.get("color", ""),
                "sort_order": sort_order,
            })
            sort_order += 1

    for i, item in enumerate(timeline_items):
        sql_parts.append(
            f"INSERT INTO fusion_timeline (id, region, region_label, event_date, title, description, color, sort_order) "
            f"VALUES ({i+1}, {sql_escape(item['region'])}, {sql_escape(item['region_label'])}, {sql_escape(item['event_date'])}, "
            f"{sql_escape(item['title'])}, {sql_escape(item['description'])}, {sql_escape(item['color'])}, {sql_escape(str(item['sort_order']))}) "
            f"ON CONFLICT (id) DO UPDATE SET region=EXCLUDED.region, region_label=EXCLUDED.region_label, event_date=EXCLUDED.event_date, "
            f"title=EXCLUDED.title, description=EXCLUDED.description, color=EXCLUDED.color, sort_order=EXCLUDED.sort_order;"
        )

    return "\n".join(sql_parts)


def generate_finance_sql(data: dict) -> str:
    """生成科技资本板块的 INSERT SQL"""
    sql_parts = []

    # highlights sections → finance_highlights
    highlight_sections = ["fed_highlights", "fx_highlights", "spacex_highlights", "ai_highlights"]
    for section in highlight_sections:
        items = data.get(section, [])
        for i, h in enumerate(items):
            sql_parts.append(
                f"INSERT INTO finance_highlights (section, label, num, sub, color, sort_order) "
                f"VALUES ({sql_escape(section)}, {sql_escape(h.get('label',''))}, {sql_escape(h.get('num',''))}, "
                f"{sql_escape(h.get('sub',''))}, {sql_escape(h.get('color',''))}, {i});"
            )

    # grid sections → finance_sections + finance_grids
    grid_sections = [
        "fed_schedule", "fed_officials", "fx_rates", "fx_cb_rates",
        "spacex_finance", "spacex_breakdown", "spacex_analyst",
        "ai_anthropic", "ai_openai", "ai_comparison"
    ]
    for idx, section in enumerate(grid_sections):
        section_data = data.get(section)
        if not section_data:
            continue

        # section metadata
        sql_parts.append(
            f"INSERT INTO finance_sections (section, tag, name, en, description, sort_order) "
            f"VALUES ({sql_escape(section)}, {sql_escape(section_data.get('tag',''))}, {sql_escape(section_data.get('name',''))}, "
            f"{sql_escape(section_data.get('en',''))}, {sql_escape(section_data.get('desc',''))}, {idx});"
        )

        # grid data
        grid = section_data.get("grid", [])
        for i, kv in enumerate(grid):
            sql_parts.append(
                f"INSERT INTO finance_grids (section, key, value, sort_order) "
                f"VALUES ({sql_escape(section)}, {sql_escape(kv.get('k',''))}, {sql_escape(kv.get('v',''))}, {i});"
            )

    return "\n".join(sql_parts)


def generate_board_sql(board_id: str) -> str:
    """生成单个板块的完整 SQL"""
    json_file = DATA_DIR / f"{board_id}.json"
    if not json_file.exists():
        return f"-- 文件不存在: {json_file}\n"

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    sql_parts = [f"-- ============ {board_id} ============\n"]

    # meta
    meta = data.get("meta", {})
    if meta:
        sql_parts.append("-- board_meta")
        sql_parts.append(generate_meta_sql(board_id, meta))
        sql_parts.append("")

    # board-specific data
    generators = {
        "rocket": generate_rocket_sql,
        "moon": generate_moon_sql,
        "semiconductor": generate_semiconductor_sql,
        "china-tech": generate_china_tech_sql,
        "mega-projects": generate_mega_projects_sql,
        "fusion": generate_fusion_sql,
        "finance": generate_finance_sql,
    }

    generator = generators.get(board_id)
    if generator:
        sql_parts.append(generator(data))

    return "\n".join(sql_parts)


def main():
    parser = argparse.ArgumentParser(description="JSON → SQL 生成脚本")
    parser.add_argument("--board", type=str, help="只生成指定板块的 SQL（如 rocket）")
    parser.add_argument("--output", type=str, help="输出到文件（默认输出到控制台）")
    args = parser.parse_args()

    boards = [args.board] if args.board else list(BOARD_MAP.keys())

    all_sql = []
    for board_id in boards:
        all_sql.append(generate_board_sql(board_id))

    output = "\n\n".join(all_sql)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"SQL 已写入: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()

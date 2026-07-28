"""
钛星 JSON → 数据库导入脚本
将 data/*.json 文件中的数据导入 Supabase 数据库

用法：
  python backend/import_json_to_db.py              # 导入所有 JSON
  python backend/import_json_to_db.py --board rocket  # 只导入火箭板块
  python backend/import_json_to_db.py --dry-run     # 预览变更，不实际写入
"""
import os
import sys
import json
import argparse
from pathlib import Path

# 添加项目根目录到 path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import get_supabase

DATA_DIR = PROJECT_ROOT / "data"

# 板块 ID 映射（JSON 文件名 → board_id）
BOARD_MAP = {
    "rocket": "rocket",
    "moon": "moon",
    "semiconductor": "semiconductor",
    "china-tech": "china-tech",
    "mega-projects": "mega-projects",
    "fusion": "fusion",
    "finance": "finance",
}


def clear_table(sb, table_name):
    """清空表（dry-run 模式下不执行）"""
    sb.table(table_name).delete().neq("id", 0).execute()
    print(f"  ✓ 清空 {table_name}")


def import_meta(sb, board_id: str, meta: dict, dry_run: bool = False):
    """导入板块元信息到 board_meta 表"""
    row = {
        "board_id": board_id,
        "updated": meta.get("updated", ""),
        "source": meta.get("source", ""),
        "module": meta.get("module", ""),
    }
    if dry_run:
        print(f"  [dry-run] INSERT board_meta: {row}")
        return
    # upsert: 如果已存在则更新
    sb.table("board_meta").upsert(row, on_conflict="board_id").execute()
    print(f"  ✓ board_meta: {board_id}")


def import_rocket(sb, data: dict, dry_run: bool = False):
    """导入火箭板块数据"""
    # comparison_table → rocket_companies
    companies = data.get("comparison_table", [])
    for i, c in enumerate(companies):
        row = {
            "id": i + 1,
            "rocket": c.get("rocket", ""),
            "company": c.get("company", ""),
            "country": c.get("country", ""),
            "fuel": c.get("fuel", ""),
            "diameter": c.get("diameter", ""),
            "thrust": c.get("thrust", ""),
            "leo": c.get("leo", ""),
            "recovery": c.get("recovery", ""),
            "status": c.get("status", ""),
            "key": c.get("key", ""),
            "sort_order": str(i),
        }
        if dry_run:
            print(f"  [dry-run] INSERT rocket_companies: {row['rocket']}")
            continue
        sb.table("rocket_companies").upsert(row, on_conflict="id").execute()
    print(f"  ✓ rocket_companies: {len(companies)} 条")

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
            "sort_order": "0",
        })
    for i, item in enumerate(data.get("timeline_2027", [])):
        timeline_items.append({
            "period": "2027",
            "event_date": item.get("date", ""),
            "title": item.get("title", ""),
            "description": item.get("desc", ""),
            "color": item.get("color", ""),
            "badge": item.get("badge", ""),
            "done": "",
            "sort_order": str(i),
        })
    for i, row in enumerate(timeline_items):
        row["id"] = i + 1
        row["sort_order"] = str(i)
        if dry_run:
            print(f"  [dry-run] INSERT rocket_timeline: {row['title']}")
            continue
        sb.table("rocket_timeline").upsert(row, on_conflict="id").execute()
    print(f"  ✓ rocket_timeline: {len(timeline_items)} 条")


def import_moon(sb, data: dict, dry_run: bool = False):
    """导入中美登月板块数据"""
    # highlights → moon_highlights
    highlights = data.get("highlights", [])
    for i, h in enumerate(highlights):
        row = {
            "id": i + 1,
            "num": h.get("num", ""),
            "label": h.get("lbl", ""),
            "color": h.get("color", ""),
            "sort_order": str(i),
        }
        if dry_run:
            print(f"  [dry-run] INSERT moon_highlights: {row['num']}")
            continue
        sb.table("moon_highlights").upsert(row, on_conflict="id").execute()
    print(f"  ✓ moon_highlights: {len(highlights)} 条")

    # comparison → moon_comparison
    comparisons = data.get("comparison", [])
    for i, c in enumerate(comparisons):
        row = {
            "id": i + 1,
            "aspect": c.get("dim", ""),
            "china_value": c.get("china", ""),
            "usa_value": c.get("us", ""),
            "notes": c.get("highlight", ""),
        }
        if dry_run:
            print(f"  [dry-run] INSERT moon_comparison: {row['aspect']}")
            continue
        sb.table("moon_comparison").upsert(row, on_conflict="id").execute()
    print(f"  ✓ moon_comparison: {len(comparisons)} 条")


def import_semiconductor(sb, data: dict, dry_run: bool = False):
    """导入半导体板块数据"""
    # highlights → semiconductor_highlights
    highlights = data.get("highlights", [])
    for i, h in enumerate(highlights):
        row = {
            "num": h.get("num", ""),
            "label": h.get("lbl", ""),
            "color": h.get("color", ""),
            "sort_order": i,
        }
        if dry_run:
            print(f"  [dry-run] INSERT semiconductor_highlights: {row['num']}")
            continue
        sb.table("semiconductor_highlights").insert(row).execute()
    print(f"  ✓ semiconductor_highlights: {len(highlights)} 条")

    # tabs → semiconductor_tab_highlights + semiconductor_tab_progress
    tabs = data.get("tabs", {})
    for tab_id, tab_data in tabs.items():
        # tab highlights
        tab_hls = tab_data.get("highlights", [])
        for i, h in enumerate(tab_hls):
            row = {
                "tab_id": tab_id,
                "num": h.get("num", ""),
                "label": h.get("lbl", ""),
                "color": h.get("color", ""),
                "sort_order": i,
            }
            if dry_run:
                print(f"  [dry-run] INSERT semiconductor_tab_highlights: {tab_id}/{row['num']}")
                continue
            sb.table("semiconductor_tab_highlights").insert(row).execute()

        # tab progress
        tab_progress = tab_data.get("progress", [])
        for i, p in enumerate(tab_progress):
            row = {
                "tab_id": tab_id,
                "year": p.get("yr", ""),
                "value": p.get("val", ""),
                "label": p.get("lbl", ""),
                "cls": p.get("cls", ""),
                "sort_order": i,
            }
            if dry_run:
                print(f"  [dry-run] INSERT semiconductor_tab_progress: {tab_id}/{row['year']}")
                continue
            sb.table("semiconductor_tab_progress").insert(row).execute()

    print(f"  ✓ semiconductor tabs: {len(tabs)} 个 tab")


def import_china_tech(sb, data: dict, dry_run: bool = False):
    """导入中国科技 AI 板块数据"""
    # highlights → china_tech_highlights
    highlights = data.get("highlights", [])
    for i, h in enumerate(highlights):
        row = {
            "num": h.get("num", ""),
            "label": h.get("lbl", ""),
            "color": h.get("color", ""),
            "sort_order": i,
        }
        if dry_run:
            print(f"  [dry-run] INSERT china_tech_highlights: {row['num']}")
            continue
        sb.table("china_tech_highlights").insert(row).execute()
    print(f"  ✓ china_tech_highlights: {len(highlights)} 条")

    # llm_table → china_tech_llm
    llm_items = data.get("llm_table", [])
    for i, item in enumerate(llm_items):
        row = {
            "model": item.get("model", ""),
            "company": item.get("company", ""),
            "params": item.get("params", ""),
            "context_window": item.get("ctx", ""),
            "coding": item.get("coding", ""),
            "math": item.get("math", ""),
            "arena": item.get("arena", ""),
            "opensource": item.get("opensource", ""),
            "price": item.get("price", ""),
            "hi_fields": item.get("hi_fields", ""),
            "sort_order": i,
        }
        if dry_run:
            print(f"  [dry-run] INSERT china_tech_llm: {row['model']}")
            continue
        sb.table("china_tech_llm").insert(row).execute()
    print(f"  ✓ china_tech_llm: {len(llm_items)} 条")


def import_mega_projects(sb, data: dict, dry_run: bool = False):
    """导入中国大工程板块数据"""
    # highlights → mega_project_highlights
    highlights = data.get("highlights", [])
    for i, h in enumerate(highlights):
        row = {
            "num": h.get("num", ""),
            "label": h.get("lbl", ""),
            "color": h.get("color", ""),
            "sort_order": i,
        }
        if dry_run:
            print(f"  [dry-run] INSERT mega_project_highlights: {row['num']}")
            continue
        sb.table("mega_project_highlights").insert(row).execute()
    print(f"  ✓ mega_project_highlights: {len(highlights)} 条")

    # timeline → mega_projects + mega_project_milestones
    timeline = data.get("timeline", [])
    project_id = 0
    milestone_id = 0
    for proj in timeline:
        project_id += 1
        proj_row = {
            "id": project_id,
            "tab_id": proj.get("tab", ""),
            "emoji": proj.get("emoji", ""),
            "project_name": proj.get("name", ""),
            "target_id": proj.get("target", ""),
            "status": proj.get("status", ""),
            "status_class": proj.get("statusClass", ""),
            "sort_order": str(project_id - 1),
        }
        if dry_run:
            print(f"  [dry-run] INSERT mega_projects: {proj_row['project_name']}")
        else:
            sb.table("mega_projects").upsert(proj_row, on_conflict="id").execute()

        # milestones
        for item in proj.get("items", []):
            milestone_id += 1
            ms_row = {
                "project_id": project_id,
                "marker": item.get("marker", ""),
                "event_date": item.get("date", ""),
                "badge": item.get("badge", ""),
                "badge_class": item.get("badgeClass", ""),
                "title": item.get("title", ""),
                "sort_order": milestone_id - 1,
            }
            if dry_run:
                print(f"  [dry-run] INSERT mega_project_milestones: {ms_row['title']}")
                continue
            sb.table("mega_project_milestones").insert(ms_row).execute()

    print(f"  ✓ mega_projects: {project_id} 个项目, {milestone_id} 个里程碑")


def import_fusion(sb, data: dict, dry_run: bool = False):
    """导入可控核聚变板块数据"""
    # highlights → fusion_highlights
    highlights = data.get("highlights", [])
    for i, h in enumerate(highlights):
        row = {
            "num": h.get("num", ""),
            "label": h.get("lbl", ""),
            "color": h.get("color", ""),
            "sort_order": i,
        }
        if dry_run:
            print(f"  [dry-run] INSERT fusion_highlights: {row['num']}")
            continue
        sb.table("fusion_highlights").insert(row).execute()
    print(f"  ✓ fusion_highlights: {len(highlights)} 条")

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
                "sort_order": str(sort_order),
            })
            sort_order += 1

    for i, row in enumerate(timeline_items):
        row["id"] = i + 1
        if dry_run:
            print(f"  [dry-run] INSERT fusion_timeline: {row['title']}")
            continue
        sb.table("fusion_timeline").upsert(row, on_conflict="id").execute()
    print(f"  ✓ fusion_timeline: {len(timeline_items)} 条")


def import_finance(sb, data: dict, dry_run: bool = False):
    """导入科技资本板块数据"""
    # 各 section 的 highlights → finance_highlights
    highlight_sections = [
        "fed_highlights", "fx_highlights", "spacex_highlights", "ai_highlights"
    ]
    for section in highlight_sections:
        items = data.get(section, [])
        for i, h in enumerate(items):
            row = {
                "section": section,
                "label": h.get("label", ""),
                "num": h.get("num", ""),
                "sub": h.get("sub", ""),
                "color": h.get("color", ""),
                "sort_order": i,
            }
            if dry_run:
                print(f"  [dry-run] INSERT finance_highlights: {section}/{row['label']}")
                continue
            sb.table("finance_highlights").insert(row).execute()
        print(f"  ✓ finance_highlights ({section}): {len(items)} 条")

    # 各 section 的 grid 数据 → finance_grids + finance_sections
    grid_sections = [
        "fed_schedule", "fed_officials", "fx_rates", "fx_cb_rates",
        "spacex_finance", "spacex_breakdown", "spacex_analyst",
        "ai_anthropic", "ai_openai", "ai_comparison"
    ]
    for section in grid_sections:
        section_data = data.get(section)
        if not section_data:
            continue

        # 写入 section 元信息
        sec_row = {
            "section": section,
            "tag": section_data.get("tag", ""),
            "name": section_data.get("name", ""),
            "en": section_data.get("en", ""),
            "description": section_data.get("desc", ""),
            "sort_order": grid_sections.index(section),
        }
        if dry_run:
            print(f"  [dry-run] INSERT finance_sections: {section}")
        else:
            sb.table("finance_sections").insert(sec_row).execute()

        # 写入 grid 数据
        grid = section_data.get("grid", [])
        for i, kv in enumerate(grid):
            row = {
                "section": section,
                "key": kv.get("k", ""),
                "value": kv.get("v", ""),
                "sort_order": i,
            }
            if dry_run:
                print(f"  [dry-run] INSERT finance_grids: {section}/{row['key']}")
                continue
            sb.table("finance_grids").insert(row).execute()
        print(f"  ✓ finance_grids ({section}): {len(grid)} 条")


def import_board(sb, board_id: str, dry_run: bool = False):
    """导入单个板块的所有数据"""
    json_file = DATA_DIR / f"{board_id}.json"
    if not json_file.exists():
        print(f" 文件不存在: {json_file}")
        return

    print(f"\n{'='*50}")
    print(f"导入板块: {board_id}")
    print(f"{'='*50}")

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. 导入 meta
    meta = data.get("meta", {})
    if meta:
        import_meta(sb, board_id, meta, dry_run)

    # 2. 根据板块导入具体数据
    importers = {
        "rocket": import_rocket,
        "moon": import_moon,
        "semiconductor": import_semiconductor,
        "china-tech": import_china_tech,
        "mega-projects": import_mega_projects,
        "fusion": import_fusion,
        "finance": import_finance,
    }

    importer = importers.get(board_id)
    if importer:
        importer(sb, data, dry_run)
    else:
        print(f"   未知板块: {board_id}")


def main():
    parser = argparse.ArgumentParser(description="JSON → 数据库导入脚本")
    parser.add_argument("--board", type=str, help="只导入指定板块（如 rocket）")
    parser.add_argument("--dry-run", action="store_true", help="预览变更，不实际写入")
    parser.add_argument("--clear", action="store_true", help="导入前先清空相关表")
    args = parser.parse_args()

    sb = get_supabase()
    boards = [args.board] if args.board else list(BOARD_MAP.keys())

    if args.dry_run:
        print("⚠️  DRY-RUN 模式：不会实际写入数据库\n")

    for board_id in boards:
        if args.clear and not args.dry_run:
            # 清空相关表（根据板块）
            table_map = {
                "rocket": ["rocket_companies", "rocket_timeline"],
                "moon": ["moon_highlights", "moon_comparison"],
                "semiconductor": ["semiconductor_highlights", "semiconductor_tab_highlights", "semiconductor_tab_progress"],
                "china-tech": ["china_tech_highlights", "china_tech_llm"],
                "mega-projects": ["mega_project_highlights", "mega_projects", "mega_project_milestones"],
                "fusion": ["fusion_highlights", "fusion_timeline"],
                "finance": ["finance_highlights", "finance_grids", "finance_sections"],
            }
            for table in table_map.get(board_id, []):
                clear_table(sb, table)

        import_board(sb, board_id, args.dry_run)

    print(f"\n{'='*50}")
    print("导入完成！")
    if args.dry_run:
        print("（dry-run 模式，未实际写入）")


if __name__ == "__main__":
    main()

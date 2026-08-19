# -*- coding: utf-8 -*-
"""
钛星本地 SQLite 建表定义（schema）

权威来源（按协调者指令）：
1. src/storage/database/shared/schema.ts（drizzle pg 定义，26 张表）
2. docs/sql/ai_extract_logs.sql（ai_extract_logs 表）
3. backend/app/db/*.py 现有代码推断（rocket_timeline 表，以及 raw_articles 的补充列）

类型约定（本地 SQLite 映射）：
- TEXT   ：文本 / varchar / date / timestamp（ISO 8601 字符串，与现有代码 datetime.now().isoformat() 一致）
- INTEGER：整数（含 id 主键、hot_score、sort_order 等）
- REAL   ：浮点（当前 schema 无 REAL 列，预留）
- JSON   ：以 TEXT 存储，写入 json.dumps、读取 json.loads（如 rocket_launch_timeline.related_news_ids）
- BOOLEAN：以 INTEGER 0/1 存储，读取转回 bool（如 latest_news.is_active、rocket_timeline.done）

所有建表/建索引语句幂等（CREATE TABLE/INDEX IF NOT EXISTS）。
"""

from typing import Dict, List, Tuple


def col(name: str, typ: str = "TEXT", constraints: str = "", **flags) -> Tuple:
    """列定义：(name, sqlite_type, constraints, flags)。flags 支持 json=True / bool=True。"""
    return (name, typ, constraints, flags)


# ========================================================================
# 表定义（顺序即建表顺序）
# ========================================================================
TABLES: Dict[str, List[Tuple]] = {
    # ---------------- 系统表（schema.ts） ----------------
    "health_check": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("updated_at", "TEXT", "DEFAULT (datetime('now'))"),
    ],
    "board_meta": [
        col("board_id", "TEXT", "PRIMARY KEY"),
        col("updated", "TEXT"),
        col("source", "TEXT"),
        col("module", "TEXT"),
    ],
    "board_status": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("board_id", "TEXT"),
        col("last_crawled_at", "TEXT"),
        col("new_items_count", "TEXT"),
        col("total_sources", "TEXT"),
        col("error_sources", "TEXT"),
        col("last_message", "TEXT"),
        col("rocket_intro", "TEXT"),
        col("rocket_next_intro", "TEXT"),
    ],

    # ---------------- 可回收火箭（schema.ts） ----------------
    "rocket_companies": [
        col("id", "INTEGER", "PRIMARY KEY"),
        col("rocket", "TEXT"),
        col("company", "TEXT"),
        col("country", "TEXT"),
        col("fuel", "TEXT"),
        col("diameter", "TEXT"),
        col("thrust", "TEXT"),
        col("leo", "TEXT"),
        col("recovery", "TEXT"),
        col("status", "TEXT"),
        col("key", "TEXT"),
        col("sort_order", "TEXT"),
    ],
    "rocket_launch_timeline": [
        col("timeline_id", "TEXT", "PRIMARY KEY"),
        col("rocket_id", "TEXT"),
        col("mission_name", "TEXT"),
        col("launch_time", "TEXT"),
        col("launch_site", "TEXT"),
        col("payload", "TEXT"),
        col("outcome", "TEXT"),
        col("reuse_status", "TEXT"),
        col("brief_desc", "TEXT"),
        col("related_news_ids", "TEXT", "", json=True),
        col("create_time", "TEXT"),
        col("update_time", "TEXT"),
    ],
    # 代码推断表：get_rocket_timeline() 查询 "rocket_timeline"，行按 period 字段（h2/2027）过滤，
    # 行结构与 data/rocket.json 的 timeline_h2/timeline_2027 条目一致（date/title/desc/color/badge/done）。
    "rocket_timeline": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("period", "TEXT"),
        col("date", "TEXT"),
        col("title", "TEXT"),
        col("desc", "TEXT"),
        col("color", "TEXT"),
        col("badge", "TEXT"),
        col("done", "INTEGER", "DEFAULT 0", bool=True),
        col("sort_order", "INTEGER", "DEFAULT 0"),
        col("created_at", "TEXT", "DEFAULT (datetime('now'))"),
    ],

    # ---------------- 中美登月（schema.ts） ----------------
    "moon_highlights": [
        col("id", "INTEGER", "PRIMARY KEY"),
        col("num", "TEXT"),
        col("label", "TEXT"),
        col("color", "TEXT"),
        col("sort_order", "TEXT"),
    ],
    "moon_comparison": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("aspect", "TEXT"),
        col("china_value", "TEXT"),
        col("usa_value", "TEXT"),
        col("notes", "TEXT"),
        col("created_at", "TEXT", "DEFAULT (datetime('now'))"),
    ],

    # ---------------- 中国半导体（schema.ts） ----------------
    "semiconductor_highlights": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("num", "TEXT", "NOT NULL"),
        col("label", "TEXT", "NOT NULL"),
        col("color", "TEXT"),
        col("sort_order", "INTEGER", "DEFAULT 0"),
    ],
    "semiconductor_tab_highlights": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("tab_id", "TEXT", "NOT NULL"),
        col("num", "TEXT", "NOT NULL"),
        col("label", "TEXT", "NOT NULL"),
        col("color", "TEXT"),
        col("sort_order", "INTEGER", "DEFAULT 0"),
    ],
    "semiconductor_tab_progress": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("tab_id", "TEXT", "NOT NULL"),
        col("year", "TEXT", "NOT NULL"),
        col("value", "TEXT"),
        col("label", "TEXT"),
        col("cls", "TEXT"),
        col("sort_order", "INTEGER", "DEFAULT 0"),
    ],
    "semiconductor_technologies": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("name", "TEXT", "NOT NULL"),
        col("category", "TEXT"),
        col("description", "TEXT"),
        col("status", "TEXT"),
        col("created_at", "TEXT", "DEFAULT (datetime('now'))"),
    ],
    "semiconductor_timeline": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("event_date", "TEXT"),
        col("company", "TEXT"),
        col("event_type", "TEXT"),
        col("description", "TEXT"),
        col("created_at", "TEXT", "DEFAULT (datetime('now'))"),
    ],

    # ---------------- 中国科技AI（schema.ts） ----------------
    "china_tech_highlights": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("num", "TEXT", "NOT NULL"),
        col("label", "TEXT", "NOT NULL"),
        col("color", "TEXT"),
        col("sort_order", "INTEGER", "DEFAULT 0"),
    ],
    "china_tech_llm": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("model", "TEXT", "NOT NULL"),
        col("company", "TEXT", "NOT NULL"),
        col("params", "TEXT"),
        col("context_window", "TEXT"),
        col("coding", "TEXT"),
        col("math", "TEXT"),
        col("arena", "TEXT"),
        col("opensource", "TEXT"),
        col("price", "TEXT"),
        col("hi_fields", "TEXT"),
        col("sort_order", "INTEGER", "DEFAULT 0"),
    ],
    "china_tech_timeline": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("event_date", "TEXT"),
        col("company", "TEXT"),
        col("event_type", "TEXT"),
        col("description", "TEXT"),
        col("created_at", "TEXT", "DEFAULT (datetime('now'))"),
    ],

    # ---------------- 中国大工程（schema.ts） ----------------
    "mega_projects": [
        col("id", "INTEGER", "PRIMARY KEY"),
        col("tab_id", "TEXT"),
        col("emoji", "TEXT"),
        col("project_name", "TEXT"),
        col("target_id", "TEXT"),
        col("status", "TEXT"),
        col("status_class", "TEXT"),
        col("sort_order", "TEXT"),
    ],
    "mega_project_highlights": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("num", "TEXT", "NOT NULL"),
        col("label", "TEXT", "NOT NULL"),
        col("color", "TEXT"),
        col("sort_order", "INTEGER", "DEFAULT 0"),
    ],
    "mega_project_milestones": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("project_id", "INTEGER", "NOT NULL"),
        col("marker", "TEXT"),
        col("event_date", "TEXT"),
        col("badge", "TEXT"),
        col("badge_class", "TEXT"),
        col("title", "TEXT"),
        col("sort_order", "INTEGER", "DEFAULT 0"),
    ],

    # ---------------- 可控核聚变（schema.ts） ----------------
    "fusion_highlights": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("num", "TEXT", "NOT NULL"),
        col("label", "TEXT", "NOT NULL"),
        col("color", "TEXT"),
        col("sort_order", "INTEGER", "DEFAULT 0"),
    ],
    "fusion_timeline": [
        col("id", "INTEGER", "PRIMARY KEY"),
        col("region", "TEXT"),
        col("region_label", "TEXT"),
        col("event_date", "TEXT"),
        col("title", "TEXT"),
        col("description", "TEXT"),
        col("color", "TEXT"),
        col("sort_order", "TEXT"),
    ],

    # ---------------- 科技资本（schema.ts） ----------------
    "finance_grids": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("section", "TEXT", "NOT NULL"),
        col("key", "TEXT", "NOT NULL"),
        col("value", "TEXT", "NOT NULL"),
        col("sort_order", "INTEGER", "DEFAULT 0"),
    ],
    "finance_highlights": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("section", "TEXT", "NOT NULL"),
        col("label", "TEXT", "NOT NULL"),
        col("num", "TEXT", "NOT NULL"),
        col("sub", "TEXT"),
        col("color", "TEXT"),
        col("sort_order", "INTEGER", "DEFAULT 0"),
    ],
    "finance_sections": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("section", "TEXT", "NOT NULL"),
        col("tag", "TEXT"),
        col("name", "TEXT"),
        col("en", "TEXT"),
        col("description", "TEXT"),
        col("sort_order", "INTEGER", "DEFAULT 0"),
    ],

    # ---------------- 新闻数据（schema.ts，raw_articles 补充代码推断列） ----------------
    # schema.ts 列：news_id/source_name/source_url/crawl_time/publish_time/title/raw_content/summary/
    #               cover_image/images/tags/category/hot_score/sentiment/event_group_id/language/status
    # 代码推断补充列（backend/app/db/articles.py 等写入）：
    #   id（select("id") 计数用）、dedup_key、board_id、source、url、date、raw_json、created_at
    # 注：news_id 在 schema.ts 为 PK；为兼容 legacy upsert_article（不带 news_id 写入）降级为可空 UNIQUE。
    "raw_articles": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("news_id", "TEXT", "UNIQUE"),
        col("source_name", "TEXT"),
        col("source_url", "TEXT"),
        col("crawl_time", "TEXT"),
        col("publish_time", "TEXT"),
        col("title", "TEXT"),
        col("raw_content", "TEXT"),
        col("summary", "TEXT"),
        col("cover_image", "TEXT"),
        col("images", "TEXT"),
        col("tags", "TEXT"),
        col("category", "TEXT"),
        col("hot_score", "INTEGER", "DEFAULT 0"),
        col("sentiment", "TEXT"),
        col("event_group_id", "TEXT"),
        col("language", "TEXT", "DEFAULT 'en'"),
        col("status", "TEXT", "DEFAULT 'pending'"),
        col("dedup_key", "TEXT", "UNIQUE"),
        col("board_id", "TEXT"),
        col("source", "TEXT"),
        col("url", "TEXT"),
        col("date", "TEXT"),
        col("raw_json", "TEXT"),
        col("created_at", "TEXT", "DEFAULT (datetime('now'))"),
    ],
    "crawl_logs": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("board_id", "TEXT"),
        col("status", "TEXT"),
        col("source_name", "TEXT"),
        col("items_count", "INTEGER", "DEFAULT 0"),
        col("error_message", "TEXT"),
        col("started_at", "TEXT"),
        col("finished_at", "TEXT"),
        col("created_at", "TEXT", "DEFAULT (datetime('now'))"),
    ],
    "latest_news": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("title", "TEXT", "NOT NULL"),
        col("summary", "TEXT", "NOT NULL"),
        col("source", "TEXT"),
        col("board", "TEXT", "NOT NULL"),
        col("board_label", "TEXT"),
        col("link", "TEXT"),
        col("publish_date", "TEXT"),
        col("sort_order", "INTEGER", "DEFAULT 0"),
        col("is_active", "INTEGER", "DEFAULT 1", bool=True),
        col("created_at", "TEXT", "DEFAULT (datetime('now'))"),
        col("updated_at", "TEXT", "DEFAULT (datetime('now'))"),
    ],

    # ---------------- AI 提取日志（docs/sql/ai_extract_logs.sql） ----------------
    "ai_extract_logs": [
        col("id", "INTEGER", "PRIMARY KEY AUTOINCREMENT"),
        col("category", "TEXT"),
        col("limit", "INTEGER"),
        col("total", "INTEGER"),
        col("inserted", "INTEGER"),
        col("failed", "INTEGER"),
        col("status", "TEXT"),
        col("message", "TEXT"),
        col("created_at", "TEXT", "DEFAULT (datetime('now'))"),
    ],
}

# (table, index_name, columns, unique)
INDEXES: List[tuple] = [
    ("raw_articles", "idx_raw_articles_status", ["status"], False),
    ("raw_articles", "idx_raw_articles_category", ["category"], False),
    ("raw_articles", "idx_raw_articles_crawl_time", ["crawl_time"], False),
    ("raw_articles", "idx_raw_articles_created_at", ["created_at"], False),
    ("crawl_logs", "idx_crawl_logs_created_at", ["created_at"], False),
    ("latest_news", "idx_latest_news_is_active", ["is_active"], False),
    ("latest_news", "idx_latest_news_sort_order", ["sort_order"], False),
    ("ai_extract_logs", "idx_ai_extract_logs_created_at", ["created_at"], False),
    ("board_status", "idx_board_status_board_id", ["board_id"], False),
    ("rocket_launch_timeline", "idx_rocket_launch_timeline_launch_time", ["launch_time"], False),
]

ALL_TABLES: List[str] = list(TABLES.keys())


def build_create_sql(name: str) -> str:
    """生成单表幂等建表 SQL"""
    if name not in TABLES:
        raise KeyError(f"[local-db] schema 未定义表: {name!r}")
    lines = []
    for cname, ctype, constraints, _flags in TABLES[name]:
        line = f'  "{cname}" {ctype}'.rstrip()
        if constraints:
            line += " " + constraints
        lines.append(line.rstrip())
    return f'CREATE TABLE IF NOT EXISTS "{name}" (\n' + ",\n".join(lines) + "\n);"


def build_index_sql(table: str, index_name: str, columns: List[str], unique: bool = False) -> str:
    cols = ", ".join(f'"{c}"' for c in columns)
    uniq = "UNIQUE " if unique else ""
    return f'CREATE {uniq}INDEX IF NOT EXISTS "{index_name}" ON "{table}" ({cols});'


def get_columns(name: str) -> List[str]:
    return [c[0] for c in TABLES[name]]


def get_column_map(name: str) -> Dict[str, Dict]:
    """列名 -> {type, json, bool}"""
    return {c[0]: {"type": c[1], "json": bool(c[3].get("json")), "bool": bool(c[3].get("bool"))} for c in TABLES[name]}


def init_db(conn) -> None:
    """执行全部建表/建索引 SQL（幂等）"""
    for name in TABLES:
        conn.execute(build_create_sql(name))
    for table, index_name, columns, unique in INDEXES:
        conn.execute(build_index_sql(table, index_name, columns, unique))
    conn.commit()


import hashlib
import os
import json
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone
from contextlib import contextmanager

# PostgreSQL 连接配置
# 开发环境使用 DEVELOP_DATABASE_URL，生产环境使用 PRODUCT_DATABASE_URL
# 如果未设置，默认使用 DEVELOP_DATABASE_URL
ENV = os.environ.get('ENV', 'develop')

if ENV == 'product':
    DATABASE_URL = os.environ.get(
        'PRODUCT_DATABASE_URL',
        'postgresql://postgres:b7Mti4WLKt5pWy8I58@cp-magic-still-ddeab31b.pg5.aidap-global.cn-beijing.volces.com:5432/postgres?sslmode=require'
    )
else:
    DATABASE_URL = os.environ.get(
        'DEVELOP_DATABASE_URL',
        'postgresql://postgres:b7Mti4WLKt5pWy8I58@cp-magic-still-ddeab31b.pg5.aidap-global.cn-beijing.volces.com:5432/postgres_dev?sslmode=require'
    )

print(f"[Database] 环境: {ENV}, 数据库: {DATABASE_URL.split('@')[1].split('/')[1].split('?')[0] if '@' in DATABASE_URL else 'unknown'}")


def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn


@contextmanager
def get_cursor():
    conn = get_db()
    try:
        yield conn.cursor()
        conn.commit()
    finally:
        conn.close()


# ============================================================
#  Schema
# ============================================================

SCHEMA = [
    # ---- 可回收火箭 ----
    """CREATE TABLE IF NOT EXISTS rocket_companies (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        rocket      TEXT NOT NULL,
        company     TEXT NOT NULL,
        country     TEXT NOT NULL,
        fuel        TEXT,
        diameter    TEXT,
        thrust      TEXT,
        leo         TEXT,
        recovery    TEXT,
        status      TEXT,
        key         TEXT UNIQUE,
        sort_order  INTEGER DEFAULT 0
    )""",

    """CREATE TABLE IF NOT EXISTS rocket_timeline (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        period      TEXT NOT NULL DEFAULT 'h2',
        event_date  TEXT NOT NULL,
        title       TEXT NOT NULL,
        description TEXT,
        color       TEXT,
        badge       TEXT,
        done        INTEGER DEFAULT 0,
        sort_order  INTEGER DEFAULT 0
    )""",
    """CREATE UNIQUE INDEX IF NOT EXISTS idx_rocket_timeline_dedup ON rocket_timeline(event_date, title)""",

    # ---- 中美登月 ----
    """CREATE TABLE IF NOT EXISTS moon_highlights (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        num         TEXT NOT NULL,
        label       TEXT NOT NULL,
        color       TEXT,
        sort_order  INTEGER DEFAULT 0
    )""",

    """CREATE TABLE IF NOT EXISTS moon_comparison (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        dimension   TEXT NOT NULL,
        china       TEXT,
        us          TEXT,
        highlight   TEXT,
        sort_order  INTEGER DEFAULT 0
    )""",

    # ---- 半导体 ----
    """CREATE TABLE IF NOT EXISTS semiconductor_highlights (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        num         TEXT NOT NULL,
        label       TEXT NOT NULL,
        color       TEXT,
        sort_order  INTEGER DEFAULT 0
    )""",

    """CREATE TABLE IF NOT EXISTS semiconductor_tab_progress (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        tab_id      TEXT NOT NULL,
        year        TEXT NOT NULL,
        value       TEXT,
        label       TEXT,
        cls         TEXT,
        sort_order  INTEGER DEFAULT 0
    )""",

    """CREATE TABLE IF NOT EXISTS semiconductor_tab_highlights (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        tab_id      TEXT NOT NULL,
        num         TEXT NOT NULL,
        label       TEXT NOT NULL,
        color       TEXT,
        sort_order  INTEGER DEFAULT 0
    )""",

    # ---- 尖端科技 (AI 大模型) ----
    """CREATE TABLE IF NOT EXISTS china_tech_highlights (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        num         TEXT NOT NULL,
        label       TEXT NOT NULL,
        color       TEXT,
        sort_order  INTEGER DEFAULT 0
    )""",

    """CREATE TABLE IF NOT EXISTS china_tech_llm (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        model       TEXT NOT NULL,
        company     TEXT NOT NULL,
        params      TEXT,
        context_window TEXT,
        coding      TEXT,
        math        TEXT,
        arena       TEXT,
        opensource  TEXT,
        price       TEXT,
        hi_fields   TEXT,
        sort_order  INTEGER DEFAULT 0
    )""",

    # ---- 大工程 ----
    """CREATE TABLE IF NOT EXISTS mega_project_highlights (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        num         TEXT NOT NULL,
        label       TEXT NOT NULL,
        color       TEXT,
        sort_order  INTEGER DEFAULT 0
    )""",

    """CREATE TABLE IF NOT EXISTS mega_projects (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        tab_id      TEXT NOT NULL,
        emoji       TEXT,
        project_name TEXT NOT NULL,
        target_id   TEXT,
        status      TEXT,
        status_class TEXT,
        sort_order  INTEGER DEFAULT 0
    )""",

    """CREATE TABLE IF NOT EXISTS mega_project_milestones (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        project_id  INTEGER NOT NULL REFERENCES mega_projects(id),
        marker      TEXT,
        event_date  TEXT,
        badge       TEXT,
        badge_class TEXT,
        title       TEXT,
        sort_order  INTEGER DEFAULT 0
    )""",

    # ---- 可控核聚变 ----
    """CREATE TABLE IF NOT EXISTS fusion_highlights (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        num         TEXT NOT NULL,
        label       TEXT NOT NULL,
        color       TEXT,
        sort_order  INTEGER DEFAULT 0
    )""",

    """CREATE TABLE IF NOT EXISTS fusion_timeline (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        region      TEXT NOT NULL,
        region_label TEXT NOT NULL,
        event_date  TEXT NOT NULL,
        title       TEXT NOT NULL,
        description TEXT,
        color       TEXT,
        sort_order  INTEGER DEFAULT 0
    )""",

    # ---- 科技资本 ----
    """CREATE TABLE IF NOT EXISTS finance_highlights (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        section     TEXT NOT NULL,
        label       TEXT NOT NULL,
        num         TEXT NOT NULL,
        sub         TEXT,
        color       TEXT,
        sort_order  INTEGER DEFAULT 0
    )""",

    """CREATE TABLE IF NOT EXISTS finance_sections (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        section     TEXT NOT NULL UNIQUE,
        tag         TEXT,
        name        TEXT,
        en          TEXT,
        description TEXT,
        sort_order  INTEGER DEFAULT 0
    )""",

    """CREATE TABLE IF NOT EXISTS finance_grids (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        section     TEXT NOT NULL,
        key         TEXT NOT NULL,
        value       TEXT NOT NULL,
        sort_order  INTEGER DEFAULT 0
    )""",

    # ---- 系统 ----
    """CREATE TABLE IF NOT EXISTS crawl_logs (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        board_id    TEXT NOT NULL,
        status      TEXT NOT NULL DEFAULT 'pending',
        message     TEXT DEFAULT '',
        crawled_at  TEXT NOT NULL DEFAULT (datetime('now'))
    )""",

    # ---- 爬虫去重 & 状态 ----
    """CREATE TABLE IF NOT EXISTS raw_articles (
        id          INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        board_id    TEXT NOT NULL,
        source      TEXT NOT NULL,
        title       TEXT NOT NULL,
        url         TEXT DEFAULT '',
        summary     TEXT DEFAULT '',
        date        TEXT DEFAULT '',
        raw_json    TEXT DEFAULT '{}',
        -- dedup key: same board + same source + same title → duplicate
        dedup_key   TEXT NOT NULL UNIQUE,
        is_new      INTEGER DEFAULT 1,
        created_at  TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE INDEX IF NOT EXISTS idx_raw_articles_board ON raw_articles(board_id, created_at DESC)""",
    """CREATE INDEX IF NOT EXISTS idx_raw_articles_dedup ON raw_articles(dedup_key)""",

    """CREATE TABLE IF NOT EXISTS board_status (
        board_id        TEXT PRIMARY KEY,
        last_crawled_at TEXT,
        new_items_count INTEGER DEFAULT 0,
        total_sources   INTEGER DEFAULT 0,
        error_sources   INTEGER DEFAULT 0,
        last_message    TEXT DEFAULT '',
        rocket_intro    TEXT DEFAULT ''
    )""",
]


def init_db():
    """Initialize all tables (idempotent)."""
    with get_cursor() as cur:
        for sql in SCHEMA:
            cur.execute(sql)
        # -- migration: add rocket_intro column to existing board_status tables --
        try:
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='board_status' AND column_name='rocket_intro'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE board_status ADD COLUMN rocket_intro TEXT DEFAULT ''")
        except Exception:
            pass  # column already exists or error


def needs_migration() -> bool:
    """Check if the DB has no data yet (first run after Docker build)."""
    try:
        with get_cursor() as cur:
            cur.execute("SELECT COUNT(*) as cnt FROM rocket_companies")
            row = cur.fetchone()
            return row['cnt'] == 0
    except Exception:
        return True


def auto_migrate():
    """Auto-run migration if DB is empty (for Docker first-run)."""
    if not needs_migration():
        return
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
    mappings = [
        # (bid, filename, migrator_func)
        ("rocket", "rocket.json", _migrate_rocket),
        ("moon", "moon.json", _migrate_moon),
        ("semiconductor", "semiconductor.json", _migrate_semiconductor),
        ("china-tech", "china-tech.json", _migrate_china_tech),
        ("mega-projects", "mega-projects.json", _migrate_mega),
        ("controlled-fusion", "fusion.json", _migrate_fusion),
        ("finance", "finance.json", _migrate_finance),
    ]
    for bid, fname, migrator in mappings:
        path = os.path.join(data_dir, fname)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            with get_cursor() as cur:
                migrator(cur, data)


def re_sync_board_from_json(board_id: str):
    """AI 更新 JSON 后，清空对应结构化表并从 JSON 重新导入到 SQLite"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

    re_sync_mappings = [
        ("rocket", "rocket.json", _migrate_rocket,
         ["rocket_companies", "rocket_timeline"]),
        ("moon", "moon.json", _migrate_moon,
         ["moon_highlights", "moon_comparison"]),
        ("semiconductor", "semiconductor.json", _migrate_semiconductor,
         ["semiconductor_highlights", "semiconductor_tab_progress", "semiconductor_tab_highlights"]),
        ("china-tech", "china-tech.json", _migrate_china_tech,
         ["china_tech_highlights", "china_tech_llm"]),
        ("mega-projects", "mega-projects.json", _migrate_mega,
         ["mega_project_highlights", "mega_projects", "mega_project_milestones"]),
        ("controlled-fusion", "fusion.json", _migrate_fusion,
         ["fusion_highlights", "fusion_timeline"]),
        ("finance", "finance.json", _migrate_finance,
         ["finance_highlights", "finance_sections", "finance_grids"]),
    ]

    for bid, fname, migrator, tables in re_sync_mappings:
        if bid != board_id:
            continue
        path = os.path.join(data_dir, fname)
        if not os.path.exists(path):
            raise FileNotFoundError(f"JSON file not found: {path}")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        with get_cursor() as cur:
            for table in tables:
                cur.execute(f"DELETE FROM {table}")
            migrator(cur, data)
        return
    raise ValueError(f"Unknown board_id: {board_id}")


def re_sync_all_from_json():
    """AI 更新完成后，从 JSON 同步全部板块到 SQLite"""
    for board_id in ["rocket", "moon", "semiconductor", "china-tech",
                      "mega-projects", "controlled-fusion", "finance"]:
        try:
            re_sync_board_from_json(board_id)
            print(f"[re-sync] {board_id} OK")
        except Exception as e:
            print(f"[re-sync] {board_id} FAILED: {e}")


def _migrate_rocket(cur, d):
    for i, r in enumerate(d.get("comparison_table", [])):
        cur.execute(
            "INSERT INTO rocket_companies (rocket,company,country,fuel,diameter,thrust,leo,recovery,status,key,sort_order) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (r["rocket"], r["company"], r["country"], r["fuel"], r["diameter"],
             r["thrust"], r["leo"], r["recovery"], r["status"], r["key"], i))
    for period, key in [("h2", "timeline_h2"), ("2027", "timeline_2027")]:
        for i, t in enumerate(d.get(key, [])):
            cur.execute(
                "INSERT INTO rocket_timeline (period,event_date,title,description,color,badge,done,sort_order) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (period, t["date"], t["title"], t.get("desc", ""), t.get("color", ""),
                 t.get("badge", ""), 1 if t.get("done") else 0, i))


def _migrate_moon(cur, d):
    for i, h in enumerate(d.get("highlights", [])):
        cur.execute("INSERT INTO moon_highlights (num,label,color,sort_order) VALUES (?,?,?,?)",
                    (h["num"], h["lbl"], h.get("color", ""), i))
    for i, c in enumerate(d.get("comparison", [])):
        cur.execute("INSERT INTO moon_comparison (dimension,china,us,highlight,sort_order) VALUES (?,?,?,?,?)",
                    (c["dim"], c["china"], c["us"], c.get("highlight", ""), i))


def _migrate_semiconductor(cur, d):
    for i, h in enumerate(d.get("highlights", [])):
        cur.execute("INSERT INTO semiconductor_highlights (num,label,color,sort_order) VALUES (?,?,?,?)",
                    (h["num"], h["lbl"], h.get("color", ""), i))
    for tab_id, content in d.get("tabs", {}).items():
        for j, p in enumerate(content.get("progress", [])):
            cur.execute("INSERT INTO semiconductor_tab_progress (tab_id,year,value,label,cls,sort_order) VALUES (?,?,?,?,?,?)",
                        (tab_id, p["yr"], p["val"], p["lbl"], p["cls"], j))
        for j, h in enumerate(content.get("highlights", [])):
            cur.execute("INSERT INTO semiconductor_tab_highlights (tab_id,num,label,color,sort_order) VALUES (?,?,?,?,?)",
                        (tab_id, h["num"], h["lbl"], h.get("color", ""), j))


def _migrate_china_tech(cur, d):
    for i, h in enumerate(d.get("highlights", [])):
        cur.execute("INSERT INTO china_tech_highlights (num,label,color,sort_order) VALUES (?,?,?,?)",
                    (h["num"], h["lbl"], h.get("color", ""), i))
    for i, llm in enumerate(d.get("llm_table", [])):
        cur.execute(
            "INSERT INTO china_tech_llm (model,company,params,context_window,coding,math,arena,opensource,price,hi_fields,sort_order) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (llm["model"], llm["company"], llm.get("params"), llm.get("ctx"),
             llm.get("coding"), llm.get("math"), llm.get("arena"),
             llm.get("opensource"), llm.get("price"),
             json.dumps(llm.get("hi_fields", []), ensure_ascii=False), i))


def _migrate_mega(cur, d):
    for i, h in enumerate(d.get("highlights", [])):
        cur.execute("INSERT INTO mega_project_highlights (num,label,color,sort_order) VALUES (?,?,?,?)",
                    (h["num"], h["lbl"], h.get("color", ""), i))
    for i, proj in enumerate(d.get("timeline", [])):
        cur.execute(
            "INSERT INTO mega_projects (tab_id,emoji,project_name,target_id,status,status_class,sort_order) "
            "VALUES (?,?,?,?,?,?,?)",
            (proj["tab"], proj.get("emoji"), proj["name"], proj.get("target"),
             proj["status"], proj.get("statusClass"), i))
        pid = cur.lastrowid
        for j, item in enumerate(proj.get("items", [])):
            cur.execute(
                "INSERT INTO mega_project_milestones (project_id,marker,event_date,badge,badge_class,title,sort_order) "
                "VALUES (?,?,?,?,?,?,?)",
                (pid, item.get("marker"), item["date"], item.get("badge"),
                 item.get("badgeClass"), item["title"], j))


def _migrate_fusion(cur, d):
    for i, h in enumerate(d.get("highlights", [])):
        cur.execute("INSERT INTO fusion_highlights (num,label,color,sort_order) VALUES (?,?,?,?)",
                    (h["num"], h["lbl"], h.get("color", ""), i))
    for region, content in d.get("timeline", {}).items():
        for j, item in enumerate(content.get("items", [])):
            cur.execute(
                "INSERT INTO fusion_timeline (region,region_label,event_date,title,description,color,sort_order) "
                "VALUES (?,?,?,?,?,?,?)",
                (region, content["label"], item["date"], item["title"],
                 item.get("desc", ""), item.get("color", ""), j))


def _migrate_finance(cur, d):
    for section in ["fed", "fx", "spacex", "ai"]:
        for i, h in enumerate(d.get(f"{section}_highlights", [])):
            cur.execute(
                "INSERT INTO finance_highlights (section,label,num,sub,color,sort_order) VALUES (?,?,?,?,?,?)",
                (section, h["label"], h["num"], h.get("sub", ""), h.get("color", ""), i))
    section_keys = [
        "fed_schedule", "fed_officials", "fx_rates", "fx_cb_rates",
        "spacex_finance", "spacex_breakdown", "spacex_analyst",
        "ai_anthropic", "ai_openai", "ai_comparison",
    ]
    for i, sk in enumerate(section_keys):
        sdata = d.get(sk, {})
        cur.execute(
            "INSERT INTO finance_sections (section,tag,name,en,description,sort_order) VALUES (?,?,?,?,?,?)",
            (sk, sdata.get("tag", ""), sdata.get("name", ""),
             sdata.get("en", ""), sdata.get("desc", ""), i))
        for j, g in enumerate(sdata.get("grid", [])):
            cur.execute("INSERT INTO finance_grids (section,key,value,sort_order) VALUES (?,?,?,?)",
                        (sk, g["k"], g["v"], j))


# ============================================================
#  Query helpers — each returns dicts matching the old JSON
# ============================================================

def _dict(row):
    return dict(row) if row else None


def _list(rows):
    return [dict(r) for r in rows]


# --- Rocket ---
def get_rocket_data() -> dict:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM rocket_companies ORDER BY sort_order, id")
        companies = _list(cur)
        cur.execute("SELECT * FROM rocket_timeline WHERE period='h2' ORDER BY sort_order, id")
        h2 = _list(cur)
        cur.execute("SELECT * FROM rocket_timeline WHERE period='2027' ORDER BY sort_order, id")
        t2027 = _list(cur)
    return {
        "meta": {"updated": "2026-07-27"},
        "comparison_table": companies,
        "timeline_h2": h2,
        "timeline_2027": t2027,
    }


# --- Moon ---
def get_moon_data() -> dict:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM moon_highlights ORDER BY sort_order, id")
        highlights = _list(cur)
        cur.execute("SELECT * FROM moon_comparison ORDER BY sort_order, id")
        comparison = _list(cur)
    return {
        "meta": {"updated": "2026-07-27", "source": "中国载人航天工程办公室、NASA、人民日报"},
        "highlights": highlights,
        "comparison": comparison,
    }


# --- Semiconductor ---
def get_semiconductor_data() -> dict:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM semiconductor_highlights ORDER BY sort_order, id")
        highlights = _list(cur)

        cur.execute("SELECT * FROM semiconductor_tab_progress ORDER BY sort_order, id")
        progress_rows = _list(cur)
        cur.execute("SELECT * FROM semiconductor_tab_highlights ORDER BY sort_order, id")
        highlight_rows = _list(cur)

    tabs = {}
    for tab_id in ["tab-mfg", "tab-eda", "tab-litho", "tab-subst"]:
        tabs[tab_id] = {
            "progress": [r for r in progress_rows if r["tab_id"] == tab_id],
            "highlights": [r for r in highlight_rows if r["tab_id"] == tab_id],
        }
    # Clean up empty keys
    for k in tabs:
        tabs[k] = {k2: v2 for k2, v2 in tabs[k].items() if v2}

    return {"meta": {"updated": "2026-07-27"}, "highlights": highlights, "tabs": tabs}


# --- China Tech ---
def get_china_tech_data() -> dict:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM china_tech_highlights ORDER BY sort_order, id")
        highlights = _list(cur)
        cur.execute("SELECT * FROM china_tech_llm ORDER BY sort_order, id")
        llm = _list(cur)
    return {
        "meta": {"updated": "2026-07-27", "source": "LMArena、Artificial Analysis、各科技企业官方"},
        "highlights": highlights,
        "llm_table": llm,
    }


# --- Mega Projects ---
def get_mega_projects_data() -> dict:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM mega_project_highlights ORDER BY sort_order, id")
        highlights = _list(cur)
        cur.execute("SELECT * FROM mega_projects ORDER BY sort_order, id")
        projects = _list(cur)

        timeline = []
        for p in projects:
            cur.execute("SELECT * FROM mega_project_milestones WHERE project_id=? ORDER BY sort_order, id", (p["id"],))
            items = _list(cur)
            timeline.append({
                "tab": p["tab_id"],
                "emoji": p["emoji"],
                "name": p["project_name"],
                "target": p["target_id"],
                "status": p["status"],
                "statusClass": p["status_class"],
                "items": items,
            })
    return {
        "meta": {"updated": "2026-07-27", "source": "国铁集团、水利部、国家发改委、国家电网、交通运输部"},
        "highlights": highlights,
        "timeline": timeline,
    }


# --- Fusion ---
def get_fusion_data() -> dict:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM fusion_highlights ORDER BY sort_order, id")
        highlights = _list(cur)
        cur.execute("SELECT * FROM fusion_timeline ORDER BY region, sort_order, id")
        rows = _list(cur)

    timeline = {}
    for r in rows:
        region = r["region"]
        if region not in timeline:
            timeline[region] = {"label": r["region_label"], "items": []}
        del r["region"], r["region_label"]
        timeline[region]["items"].append(r)

    return {
        "meta": {"updated": "2026-07-27", "source": "ITER、CFS、中核集团、核聚变中心"},
        "highlights": highlights,
        "timeline": timeline,
    }


# --- Finance ---
def get_finance_data() -> dict:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM finance_highlights ORDER BY sort_order, id")
        hl_rows = _list(cur)
        cur.execute("SELECT * FROM finance_sections ORDER BY sort_order, id")
        sec_rows = _list(cur)
        cur.execute("SELECT * FROM finance_grids ORDER BY sort_order, id")
        grid_rows = _list(cur)

    result = {"meta": {"updated": "2026-07-27T00:53:28+08:00", "module": "finance"}}

    # Highlights grouped by section
    for s in ["fed", "fx", "spacex", "ai"]:
        result[s + "_highlights"] = [h for h in hl_rows if h["section"] == s]

    # Sections + grids
    for sec in sec_rows:
        section_name = sec["section"]
        grid = [{"k": g["key"], "v": g["value"]} for g in grid_rows if g["section"] == section_name]
        entry = {
            "tag": sec["tag"],
            "name": sec["name"],
            "en": sec["en"],
            "grid": grid,
        }
        if sec["description"]:
            entry["desc"] = sec["description"]
        result[section_name] = entry

    return result


# ============================================================
#  Board registry
# ============================================================

BOARD_GETTERS = {
    "rocket": get_rocket_data,
    "moon": get_moon_data,
    "semiconductor": get_semiconductor_data,
    "china-tech": get_china_tech_data,
    "mega-projects": get_mega_projects_data,
    "controlled-fusion": get_fusion_data,
    "finance": get_finance_data,
}

BOARD_NAMES_ZH = {
    "rocket": "可回收火箭",
    "moon": "中美登月",
    "semiconductor": "半导体",
    "china-tech": "尖端科技",
    "mega-projects": "大工程",
    "controlled-fusion": "可控核聚变",
    "finance": "科技资本",
}


def get_board(bid: str) -> dict | None:
    getter = BOARD_GETTERS.get(bid)
    if getter is None:
        return None
    return getter()


def list_boards() -> list:
    result = []
    for bid, getter in BOARD_GETTERS.items():
        data = getter()
        result.append({
            "board_id": bid,
            "name": BOARD_NAMES_ZH.get(bid, bid),
            "updated_at": data.get("meta", {}).get("updated", ""),
        })
    return result


# ============================================================
#  Crawl log
# ============================================================

def log_crawl(bid: str, status: str, message: str = ""):
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO crawl_logs (board_id, status, message) VALUES (?, ?, ?)",
            (bid, status, message)
        )


# ============================================================
#  爬虫去重 & 状态管理
# ============================================================

def _make_dedup_key(board_id: str, source: str, title: str) -> str:
    """生成去重 key：board_id + source + title 的 SHA256（取前 32 位）"""
    raw = f"{board_id}|{source}|{title.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def upsert_article(board_id: str, source: str, title: str,
                   url: str = "", summary: str = "", date: str = "",
                   raw_json: str = "{}") -> bool:
    """
    去重写入一条爬取到的文章/事件。
    返回 True = 新数据已入库；False = 重复，跳过。
    """
    dedup_key = _make_dedup_key(board_id, source, title)
    with get_cursor() as cur:
        # 检查是否已存在
        cur.execute("SELECT id FROM raw_articles WHERE dedup_key=?", (dedup_key,))
        if cur.fetchone():
            return False  # 重复，跳过

        cur.execute(
            """INSERT INTO raw_articles
               (board_id, source, title, url, summary, date, raw_json, dedup_key)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (board_id, source, title, url, summary, date, raw_json, dedup_key)
        )
        return True


def update_board_status(board_id: str, new_count: int,
                        total_sources: int = 0, error_sources: int = 0,
                        message: str = ""):
    """更新板块爬取状态"""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO board_status (board_id, last_crawled_at, new_items_count,
                                      total_sources, error_sources, last_message)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(board_id) DO UPDATE SET
                last_crawled_at = excluded.last_crawled_at,
                new_items_count = excluded.new_items_count,
                total_sources   = excluded.total_sources,
                error_sources   = excluded.error_sources,
                last_message    = excluded.last_message
        """, (board_id, now, new_count, total_sources, error_sources, message))


def get_board_status(board_id: str) -> dict | None:
    """查询某个板块的爬取状态"""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM board_status WHERE board_id=?", (board_id,))
        row = cur.fetchone()
        return _dict(row)


def get_recent_articles(board_id: str, limit: int = 20) -> list:
    """获取板块最近抓取的文章列表"""
    with get_cursor() as cur:
        cur.execute(
            """SELECT id, board_id, source, title, url, summary, date, is_new, created_at
               FROM raw_articles WHERE board_id=?
               ORDER BY created_at DESC LIMIT ?""",
            (board_id, limit)
        )
        return _list(cur)


def get_articles_stats(board_id: str) -> dict:
    """统计板块文章：总数 + 最新抓取时间"""
    with get_cursor() as cur:
        cur.execute(
            "SELECT COUNT(*), MAX(created_at) FROM raw_articles WHERE board_id=?",
            (board_id,)
        )
        total, latest = cur.fetchone()
    return {"total_articles": total or 0, "latest_crawl": latest or ""}


def get_global_last_updated() -> str:
    """取所有板块中最近一次爬取成功的时间，格式化为中文日期。"""
    with get_cursor() as cur:
        cur.execute("SELECT MAX(last_crawled_at) FROM board_status")
        row = cur.fetchone()
    latest = row[0] if row else None
    if not latest:
        return "暂无数据"
    try:
        dt = datetime.fromisoformat(latest)
        return dt.strftime("%Y年%m月%d日 %H:%M")
    except (ValueError, TypeError):
        # 兼容旧格式 YYYY-MM-DD HH:MM:SS
        try:
            dt = datetime.strptime(latest, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y年%m月%d日 %H:%M")
        except (ValueError, TypeError):
            return latest


def _classify_crawled_item(item: dict) -> tuple[str, str, str, str, str, str]:
    """
    从爬虫返回的字典中提取统一的 (title, url, summary, date, raw_json) 字段。
    自动适配不同爬虫返回的不同 key 名称。
    """
    title = (item.get("title") or item.get("name") or
             item.get("headline") or item.get("event") or "")
    url = (item.get("url") or item.get("link") or
           item.get("href") or item.get("source_url") or "")
    summary = (item.get("summary") or item.get("desc") or
               item.get("description") or item.get("content") or
               item.get("mission") or "")
    date = (item.get("date") or item.get("published") or
            item.get("net") or item.get("event_date") or "")
    raw_json = json.dumps(item, ensure_ascii=False, default=str)
    return title, url, summary, date, raw_json


# ============================================================
#  Rocket 结构化表同步（从 Launch API → rocket_timeline）
# ============================================================

# 机构 → 国家颜色
_AGENCY_COLOR = {
    "SpaceX": "", "Blue Origin": "", "Rocket Lab": "", "ULA": "",
    "Firefly": "", "Relativity Space": "", "Stoke Space": "",
    "CASC": "amber",
    "LandSpace": "amber", "Galactic Energy": "amber",
    "Space Pioneer": "amber", "iSpace": "amber", "ExPace": "amber",
}

# 机构 → 徽章
_AGENCY_BADGE = {
    "CASC": "国家队",
    "LandSpace": "民营", "Galactic Energy": "民营",
    "Space Pioneer": "民营", "iSpace": "民营", "ExPace": "民营",
}


def sync_launch_api_to_timeline() -> int:
    """爬虫后处理：将 Launch Library API 数据同步到 rocket_timeline。

    直接调用 crawlers.rocket 的 crawl_rocket_launches 和 crawl_spacex，
    把每条发射计划映射为 timeline 行 (upsert 去重)。

    返回新增行数。
    """
    import sys, os, importlib
    root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)

    mod = importlib.import_module("crawlers.rocket")
    items = []
    for fn_name in ("crawl_rocket_launches", "crawl_spacex"):
        try:
            items.extend(getattr(mod, fn_name)() or [])
        except Exception:
            pass  # 单个源失败不阻塞

    new_count = 0
    with get_cursor() as cur:
        for item in items:
            date_str = item.get("date", "")
            if not date_str or not date_str.startswith(("2026", "2027")):
                continue

            # 2026-07-28 → 2026.07.28
            event_date = date_str.replace("-", ".")

            # 判断 period
            if date_str[:4] == "2027":
                period = "2027"
            elif date_str >= "2026-07-01":
                period = "h2"
            else:
                continue  # 跳过上半年已过去的

            agency = item.get("agency", "")
            rocket_name = item.get("rocket", "")
            mission = item.get("mission", "")
            title = item.get("title", "")
            if mission and mission not in title:
                title = f"{title} · {mission}"
            if rocket_name and rocket_name not in title:
                title = f"{rocket_name} · {title}"

            status = (item.get("status") or "").lower()
            done = 1 if any(w in status for w in ("success", "launched", "complete")) else 0

            color = _AGENCY_COLOR.get(agency, "")
            badge = _AGENCY_BADGE.get(agency, "")
            summary = (item.get("summary") or "")[:300]

            # 去重 upsert
            cur.execute(
                "SELECT id FROM rocket_timeline WHERE event_date=? AND title=?",
                (event_date, title))
            if cur.fetchone():
                continue

            cur.execute(
                "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM rocket_timeline WHERE period=?",
                (period,))
            next_order = cur.fetchone()[0]

            cur.execute(
                """INSERT INTO rocket_timeline
                   (period, event_date, title, description, color, badge, done, sort_order)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (period, event_date, title, summary, color, badge, done, next_order))
            new_count += 1

    return new_count


# ============================================================
#  Rocket 结构化表同步（从 Launch Library API → rocket_companies）
# ============================================================

# key → (config_id, 显示名称, 公司名)
_COMPANY_CONFIGS = {
    "falcon9":      (164, "猎鹰9号 Block 5", "SpaceX"),
    "falcon_heavy": (161, "猎鹰重型", "SpaceX"),
    "starship":     (528, "星舰 V3", "SpaceX"),
    "newglenn":     (138, "新格伦", "Blue Origin"),
    "electron":     (26,  "Electron", "Rocket Lab"),
    "neutron":      (476, "Neutron", "Rocket Lab"),
    "terran_r":     (482, "Terran R", "Relativity Space"),
    "nova":         (533, "Nova", "Stoke Space"),
    "zq2e":         (519, "朱雀二号E", "蓝箭航天"),
    "zq3":          (539, "朱雀三号", "蓝箭航天"),
    "cz10b":        (554, "长征十号乙", "航天科技集团"),
    "cz12a":        (538, "长征十二号甲", "中国商火"),
    "ceres1":       (461, "谷神星一号", "星河动力"),
    "ceres2":       (546, "谷神星二号", "星河动力"),
}


def sync_rocket_companies() -> int:
    """从 Launch Library 2 API 同步火箭技术参数到 rocket_companies 表。

    每次调用会请求 LL2 详情端点获取 14 款火箭的最新参数（直径、推力、
    LEO 运力、发射次数等），并以 key 为唯一标识 UPSERT 更新定量字段，
    不覆盖人工维护的 fuel 等字段。

    返回成功更新的火箭数。
    """
    import requests as _requests

    # 避免被系统代理拦截（沙箱环境常见问题）
    session = _requests.Session()
    session.trust_env = False

    updated = 0
    for key, (config_id, rocket_name, company_name) in _COMPANY_CONFIGS.items():
        try:
            resp = session.get(
                f"https://ll.thespacedevs.com/2.2.0/config/launcher/{config_id}/",
                timeout=15,
                headers={"User-Agent": "taixing/1.0"},
            )
            if resp.status_code != 200:
                continue
            data = resp.json()

            mfr = data.get("manufacturer", {})
            country = "美国" if mfr.get("country_code") == "USA" else "中国"

            # 直径 (m)
            dia = data.get("diameter")
            diameter = f"{dia}m" if dia else None

            # 推力 kN → 吨 (÷10)
            thrust_kn = data.get("to_thrust")
            thrust = f"~{int(thrust_kn / 10)}t" if thrust_kn else None

            # LEO 运力 kg → 吨
            leo_kg = data.get("leo_capacity")
            if leo_kg and leo_kg > 0:
                leo = f"{leo_kg / 1000:.1f}t" if leo_kg >= 1000 else f"{leo_kg}kg"
            else:
                leo = None

            # 回收方式
            recovery = "可回收" if data.get("reusable") else None

            # 状态推断
            total = data.get("total_launch_count", 0) or 0
            active = data.get("active", False)
            if total >= 100:
                status = "成熟运营"
            elif total >= 10:
                status = f"已发射{total}次"
            elif total > 0:
                status = f"已发射{total}次"
            elif active:
                status = "研制中"
            else:
                status = "规划中"

            # sort_order: 按 LEO 运力降序
            sort_order = int(leo_kg or 0)

            with get_cursor() as cur:
                cur.execute("""
                    INSERT INTO rocket_companies
                        (rocket, company, country, diameter, thrust, leo,
                         recovery, status, key, sort_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        rocket   = excluded.rocket,
                        company  = excluded.company,
                        country  = excluded.country,
                        diameter = COALESCE(excluded.diameter, rocket_companies.diameter),
                        thrust   = COALESCE(excluded.thrust, rocket_companies.thrust),
                        leo      = COALESCE(excluded.leo, rocket_companies.leo),
                        recovery = COALESCE(excluded.recovery, rocket_companies.recovery),
                        status   = excluded.status
                """, (rocket_name, company_name, country, diameter, thrust, leo,
                      recovery, status, key, sort_order))
                updated += 1
        except Exception:
            continue  # 单个 API 失败不阻塞其他

    return updated


# ============================================================
#  Rocket 引言（AI 动态更新）
# ============================================================

_DEFAULT_ROCKET_INTRO = '<p>火箭一子级造价占全箭约 70%——过去打完就扔，相当于\u201c用黄金造一次性筷子\u201d。可回收火箭把消耗品变成可反复使用的\u201c太空交通工具\u201d，复用 10 次以上成本可直降 80%。这不仅是技术突破，更是航天经济学的底层重写。</p>\n<p>截至 2026 年 7 月，全球已形成 <strong>美国领跑、中国国家突击、民营多线并进</strong> 的格局。下面逐家拆解最新进展。</p>'


def get_rocket_intro() -> str:
    """读取 rocket 板块引言，若未设置则返回默认值。"""
    with get_cursor() as cur:
        cur.execute("SELECT rocket_intro FROM board_status WHERE board_id='rocket'")
        row = cur.fetchone()
    if row and row["rocket_intro"]:
        return row["rocket_intro"]
    return _DEFAULT_ROCKET_INTRO


def set_rocket_intro(text: str):
    """更新 rocket 板块引言（AI 生成后写入）。"""
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO board_status (board_id, rocket_intro)
            VALUES ('rocket', ?)
            ON CONFLICT(board_id) DO UPDATE SET rocket_intro = excluded.rocket_intro
        """, (text,))

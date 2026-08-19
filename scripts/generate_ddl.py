#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从本地 schema（backend/app/db/local/schema.py）生成 PostgreSQL DDL，
用于在 Coze 的 Supabase（开发/生产）数据库执行，同步表结构。

用法：
    python scripts/generate_ddl.py              # 输出全部表的 DDL（复制到 Coze 执行）
    python scripts/generate_ddl.py --tables raw_articles,board_meta   # 只输出指定表
    python scripts/generate_ddl.py --check      # 只打印表清单摘要，不输出 SQL
    python scripts/generate_ddl.py --sync prod  # 直接连生产库自动同步（读 .env.local）
    python scripts/generate_ddl.py --sync dev   # 直接连开发库自动同步
    python scripts/generate_ddl.py --diff prod  # 只对比生产库差异，不执行

特点：
- 幂等：CREATE TABLE IF NOT EXISTS + ALTER TABLE ADD COLUMN IF NOT EXISTS，
  已存在的表/列跳过，重复执行安全，不破坏已有数据。
- --sync 模式从项目根 .env.local 读取 DB_PROD_URL / DB_DEV_URL 连接串（已 gitignore）。
- raw_articles.id 故意不补（生产主键是 news_id，代码不依赖 id）。
"""
import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.local import schema  # noqa: E402

# raw_articles.id 有意不补（生产主键是 news_id）
SKIP_COLUMNS = {"raw_articles": {"id"}}


def _load_env_local():
    """从 .env.local 读取 DB_PROD_URL / DB_DEV_URL"""
    env_file = PROJECT_ROOT / ".env.local"
    if not env_file.exists():
        return {}
    result = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        result[k.strip()] = v.strip()
    return result


# SQLite 类型 → PostgreSQL 类型映射
def pg_type(sqlite_type: str, constraints: str, flags: dict) -> str:
    t = sqlite_type.upper()
    if flags.get("json"):
        return "JSONB"
    if flags.get("bool"):
        return "BOOLEAN"
    if t == "INTEGER":
        if "AUTOINCREMENT" in constraints.upper():
            return "BIGSERIAL"
        return "INTEGER"
    if t == "REAL":
        return "DOUBLE PRECISION"
    return "TEXT"  # TEXT / VARCHAR / DATE / TIMESTAMP 统一按 TEXT（与代码 ISO 字符串一致）


def col_pg_def(col_def) -> str:
    name, sqlite_type, constraints, flags = col_def
    typ = pg_type(sqlite_type, constraints, flags)
    parts = [f'"{name}"', typ]
    # 主键
    if "PRIMARY KEY" in constraints.upper():
        if "AUTOINCREMENT" in constraints.upper():
            parts = [f'"{name}"', "BIGSERIAL PRIMARY KEY"]  # 自增主键
        else:
            parts.append("PRIMARY KEY")
    return " ".join(parts)


def generate_ddl(table_names=None):
    """返回 (create_statements, alter_statements, table_count)"""
    creates = []
    alters = []
    count = 0
    for tname, cols in schema.TABLES.items():
        if table_names and tname not in table_names:
            continue
        count += 1
        # CREATE TABLE IF NOT EXISTS（完整列定义；已存在的表不重建）
        col_defs = [col_pg_def(c) for c in cols]
        creates.append(
            f'CREATE TABLE IF NOT EXISTS "{tname}" (\n  ' + ",\n  ".join(col_defs) + "\n);"
        )
        # ALTER TABLE ADD COLUMN IF NOT EXISTS（补齐已有表缺失的列）
        for c in cols:
            name, sqlite_type, constraints, flags = c
            if "PRIMARY KEY" in constraints.upper():
                continue  # 主键列不补（建表时已定义）
            typ = pg_type(sqlite_type, constraints, flags)
            alters.append(
                f'ALTER TABLE "{tname}" ADD COLUMN IF NOT EXISTS "{name}" {typ};'
            )
    return creates, alters, count


def _connect_db(env):
    """从 .env.local 读取连接串并连接数据库。env: 'prod' 或 'dev'"""
    env_vars = _load_env_local()
    key = "DB_PROD_URL" if env == "prod" else "DB_DEV_URL"
    dsn = env_vars.get(key)
    if not dsn:
        print(f"❌ .env.local 里没找到 {key}，请先配置连接串")
        sys.exit(1)
    try:
        import psycopg2
    except ImportError:
        print("❌ 缺少 psycopg2，请先 pip install psycopg2-binary")
        sys.exit(1)
    conn = psycopg2.connect(dsn, connect_timeout=20)
    return conn


def _diff_db(conn):
    """对比数据库 vs 本地 schema，返回 (缺表, 缺列字典)"""
    cur = conn.cursor()
    cur.execute("""SELECT table_name, column_name FROM information_schema.columns
                   WHERE table_schema='public'""")
    prod = {}
    for t, c in cur.fetchall():
        prod.setdefault(t, set()).add(c)
    cur.close()

    local_tables = set(schema.TABLES)
    prod_tables = set(prod)
    missing_tables = sorted(local_tables - prod_tables)
    missing_cols = {}
    for t in sorted(local_tables & prod_tables):
        skip = SKIP_COLUMNS.get(t, set())
        local_cols = {c[0] for c in schema.TABLES[t]} - skip
        diff = sorted(local_cols - prod.get(t, set()))
        if diff:
            missing_cols[t] = diff
    return missing_tables, missing_cols


def _sync_db(env, execute=True):
    """连库对比并（可选）执行同步"""
    conn = _connect_db(env)
    label = "生产" if env == "prod" else "开发"
    print(f"=== {label}库（{env}）{'同步' if execute else '对比'} ===")
    missing_tables, missing_cols = _diff_db(conn)

    if not missing_tables and not missing_cols:
        print("✅ 表结构已对齐，无需同步")
        conn.close()
        return

    print(f"缺表: {missing_tables or '无'}")
    print(f"缺列: {missing_cols or '无'}")

    if not execute:
        conn.close()
        return

    conn.commit()  # 结束 _diff_db 的只读事务，之后才能设 autocommit
    conn.autocommit = True
    cur = conn.cursor()

    # 建缺表
    for t in missing_tables:
        col_defs = [col_pg_def(c) for c in schema.TABLES[t]]
        sql = f'CREATE TABLE IF NOT EXISTS "{t}" (\n  ' + ",\n  ".join(col_defs) + "\n);"
        print(f"[创建表] {t}")
        cur.execute(sql)

    # 补缺列（排除 SKIP_COLUMNS）
    for t, cols in missing_cols.items():
        for cname in cols:
            cd = next((c for c in schema.TABLES[t] if c[0] == cname), None)
            if not cd:
                continue
            name, stype, cons, flags = cd
            typ = pg_type(stype, cons, flags)
            print(f"[加列] {t}.{cname} {typ}")
            cur.execute(f'ALTER TABLE "{t}" ADD COLUMN IF NOT EXISTS "{cname}" {typ}')

    cur.close()
    conn.close()
    print(f"\n✅ {label}库同步完成")


def main():
    parser = argparse.ArgumentParser(description="生成/同步 Supabase (PostgreSQL) 表结构 DDL")
    parser.add_argument("--tables", help="只处理指定表，逗号分隔，如 raw_articles,board_meta")
    parser.add_argument("--check", action="store_true", help="只打印本地表清单，不输出 SQL")
    parser.add_argument("--sync", choices=["prod", "dev"], help="直接连库自动同步（读 .env.local）")
    parser.add_argument("--diff", choices=["prod", "dev"], help="只对比数据库差异，不执行")
    args = parser.parse_args()

    if args.sync:
        _sync_db(args.sync, execute=True)
        return
    if args.diff:
        _sync_db(args.diff, execute=False)
        return

    table_names = set(t.strip() for t in args.tables.split(",")) if args.tables else None

    if args.check:
        print(f"共 {len(schema.TABLES)} 张表（本地 schema 定义）：")
        for tname in schema.TABLES:
            mark = " [指定]" if table_names and tname in table_names else ""
            print(f"  {tname}{mark}")
        print("\n提示：表已存在则 CREATE IF NOT EXISTS 跳过；缺列用 ALTER ADD COLUMN IF NOT EXISTS 补齐。")
        return

    creates, alters, n = generate_ddl(table_names)
    print(f"-- 钛星表结构同步 DDL（{n} 张表）--")
    print("-- 用法：复制以下全部内容到 Coze 的 SQL 执行框运行（开发/生产各一次）--")
    print("-- 幂等：重复执行安全 --")
    print("-- ========== 建表（不存在的表才建） ==========")
    for s in creates:
        print(s)
        print()
    print("-- ========== 补列（已存在的表缺列才补） ==========")
    for s in alters:
        print(s)


if __name__ == "__main__":
    main()

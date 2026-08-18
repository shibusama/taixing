#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从本地 schema（backend/app/db/local/schema.py）生成 PostgreSQL DDL，
用于在 Coze 的 Supabase（开发/生产）数据库执行，同步表结构。

用法：
    python scripts/generate_ddl.py              # 输出全部表的 DDL
    python scripts/generate_ddl.py --tables raw_articles,board_meta   # 只输出指定表
    python scripts/generate_ddl.py --check      # 只打印表清单摘要，不输出 SQL

特点：
- 幂等：CREATE TABLE IF NOT EXISTS + ALTER TABLE ADD COLUMN IF NOT EXISTS，
  已存在的表/列跳过，重复执行安全，不破坏已有数据。
- 用法：把输出复制到 Coze 平台的 SQL 执行框运行即可（开发/生产各跑一次）。
"""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# schema 模块在 backend/app/db/local/ 下，需要 backend/ 在 sys.path
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.local import schema  # noqa: E402


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


def main():
    parser = argparse.ArgumentParser(description="生成 Supabase (PostgreSQL) 表结构同步 DDL")
    parser.add_argument("--tables", help="只处理指定表，逗号分隔，如 raw_articles,board_meta")
    parser.add_argument("--check", action="store_true", help="只打印表清单，不输出 SQL")
    args = parser.parse_args()

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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地 SQLite 种子脚本：把 data/*.json 通过 re_sync_all_from_json 灌入 .local/taixing.db。

幂等：json_sync 按各表唯一键「先查后插/更新」，重复执行不产生重复行。
用法：
    python scripts/seed_local_db.py            # 灌入全部 7 个版块
    python scripts/seed_local_db.py rocket     # 只灌入指定版块
"""
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# backend/app 包（app.db.* / app.routers.*）需要 backend/ 在 sys.path
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _table_counts(db_path: Path) -> dict:
    """读取本地库各业务表行数（排除 sqlite_* 系统表）"""
    conn = sqlite3.connect(str(db_path))
    try:
        tables = [
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        counts = {}
        for t in tables:
            counts[t] = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        return counts
    finally:
        conn.close()


def main() -> None:
    from app.db.client import get_db_mode, get_supabase, init_db
    from app.db.board_data import re_sync_all_from_json, re_sync_board_from_json

    board_id = sys.argv[1] if len(sys.argv) > 1 else None

    print(f"[seed_local_db] 数据库模式: {get_db_mode()}")
    init_db()

    result = re_sync_board_from_json(board_id) if board_id else re_sync_all_from_json()

    print("[seed_local_db] 同步结果（各表写入/更新条数）:")
    for k, v in result.items():
        if k in ("status", "skipped"):
            continue
        print(f"  {k}: {v}")
    if result.get("skipped"):
        print("[seed_local_db] skipped:")
        for s in result["skipped"]:
            print(f"  - {s}")

    sb = get_supabase()
    db_path = getattr(sb, "db_path", None)
    if db_path is not None:
        counts = _table_counts(Path(db_path))
        print(f"[seed_local_db] 表数据量（{db_path}）:")
        for t, n in counts.items():
            if n:
                print(f"  {t}: {n}")
        print(f"[seed_local_db] 非空表 {sum(1 for n in counts.values() if n)} 张 / 共 {len(counts)} 张")
    print("[seed_local_db] 完成")


if __name__ == "__main__":
    main()
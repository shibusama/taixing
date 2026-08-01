# -*- coding: utf-8 -*-
"""
本地数据库种子入口（预留骨架）

说明：本次不实现具体灌入逻辑。
后续由 re_sync_all_from_json / re_sync_board_from_json（backend/app/db/board_data.py）
把 data/*.json 灌入本地 SQLite（.local/taixing.db），或由 scripts/seed_local_db.py 调用本函数。
"""


def seed_from_json(board_id: str = None, db_path=None) -> dict:
    """从 data/*.json 灌入本地库（骨架，未实现）。

    Args:
        board_id: 指定板块（None 表示全部）
        db_path:  数据库文件路径（None 使用默认 .local/taixing.db）

    Returns:
        执行结果 dict。当前仅返回 not_implemented 占位。
    """
    return {
        "status": "not_implemented",
        "board_id": board_id,
        "message": "seed_from_json 尚未实现：后续由 re_sync_all_from_json / re_sync_board_from_json 灌入 data/*.json",
    }

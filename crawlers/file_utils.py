"""
JSON 文件读写工具模块
提供 JSON 文件的加载、保存、元数据更新等功能。
"""

import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"


def load_json(filename):
    """从 data/ 目录加载 JSON 文件"""
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename, data):
    """保存数据到 data/ 目录下的 JSON 文件"""
    with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_meta(data):
    """更新 JSON 数据中的 meta.updated 字段为当前时间"""
    if "meta" in data:
        data["meta"]["updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")

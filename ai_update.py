#!/usr/bin/env python3
"""
钛星网站 AI 数据解读脚本
读取 fetch_data.py 抓取的快照，调用 DeepSeek API 自动解读并更新 JSON。

用法：
    python ai_update.py              # 解读全部板块
    python ai_update.py rocket       # 只解读火箭板块
    python ai_update.py fusion       # 只解读核聚变板块
    python ai_update.py --dry-run    # 只显示变更建议，不写入JSON
    python ai_update.py rocket --dry-run  # 组合使用

依赖：pip install requests
配置：API Key 已硬编码在 get_api_key() 函数中
"""

import json
import os
import re
import sys
import shutil
import requests
from datetime import datetime
from pathlib import Path
from collections.abc import Mapping

# ============ 路径配置 ============
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SNAPSHOT_DIR = DATA_DIR / "_snapshots"
BACKUP_DIR = DATA_DIR / "_backups"

# ============ API 配置 ============
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# ============ 板块配置 ============
# 每个板块对应一个 JSON 文件和若干快照源
BOARDS = {
    "rocket": {
        "json_file": "rocket.json",
        "snapshots": ["spacex_launches", "blue_origin", "rocket_lab", "rocket_launches"],
        "desc": "可回收火箭进展",
        "hint": "关注：星舰试飞新进展、朱雀三号回收结果、智神星首飞、长征十号乙复用、各民营火箭发射动态",
    },
    "moon": {
        "json_file": "moon.json",
        "snapshots": ["nasa_artemis"],
        "desc": "中美登月竞赛",
        "hint": "关注：Artemis任务进展、嫦娥七号发射时间、载人登月最新时间表",
    },
    "fusion": {
        "json_file": "fusion.json",
        "snapshots": ["iter_newsline", "cfs_commonwealth", "asipp_news"],
        "desc": "可控核聚变",
        "hint": "关注：ITER建造新里程碑、CFS SPARC进度、EAST/环流三号新纪录、Helion进展",
    },
    "semiconductor": {
        "json_file": "semiconductor.json",
        "snapshots": ["smic_news", "smee_news"],
        "desc": "中国半导体",
        "hint": "关注：中芯国际新工艺量产、上海微电子光刻机交付、国产替代新进展",
    },
    "china-tech": {
        "json_file": "china-tech.json",
        "snapshots": ["deepseek_blog", "moonshot_blog"],
        "desc": "中国科技AI",
        "hint": "关注：DeepSeek/Kimi/智谱等新模型发布、参数性能突破、IPO估值进展",
    },
    "mega-projects": {
        "json_file": "mega-projects.json",
        "snapshots": ["china_railway"],
        "desc": "中国大工程",
        "hint": "关注：平陆运河通航进度、川藏铁路隧道贯通、三峡新通道、跨海通道进展",
    },
    "finance": {
        "json_file": "finance.json",
        "snapshots": ["anthropic_news", "openai_blog"],
        "desc": "科技资本",
        "hint": "关注：AI公司估值/IPO最新进展、美联储政策变化。注意：汇率已由fetch_data.py自动更新，不要改汇率数据",
    },
}

# ============ 工具函数 ============

def get_api_key():
    """获取 DeepSeek API Key"""
    return "sk-REMOVED"


def load_json(filename):
    """加载 JSON 文件"""
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename, data):
    """保存 JSON 文件（UTF-8 + 2空格缩进）"""
    with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def backup_json(filename):
    """写入前创建备份"""
    src = DATA_DIR / filename
    if src.exists():
        BACKUP_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = BACKUP_DIR / f"{filename}.{ts}.bak"
        shutil.copy2(src, dst)
        return dst
    return None


def find_latest_snapshot(prefix):
    """查找最新的快照文件（按文件名时间戳排序）"""
    if not SNAPSHOT_DIR.exists():
        return None
    files = sorted(SNAPSHOT_DIR.glob(f"{prefix}_*.json"), reverse=True)
    return files[0] if files else None


def format_snapshot(snap_path, max_chars=4000):
    """将快照内容格式化为 AI 可读的文本"""
    with open(snap_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    lines = []
    lines.append(f"### 来源: {snap_path.stem}")

    if isinstance(data, list):
        # 火箭发射列表等
        lines.append(f"（共 {len(data)} 条记录，显示前 15 条）")
        for item in data[:15]:
            date = item.get("date", "")
            agency = item.get("agency", "")
            name = item.get("name", "")
            status = item.get("status", "")
            lines.append(f"- [{date}] {agency} | {name} | 状态: {status}")
            if item.get("mission"):
                lines.append(f"  任务: {item['mission']}")
            if item.get("description"):
                lines.append(f"  描述: {item['description'][:200]}")
    elif isinstance(data, dict):
        # 网页快照
        if data.get("url"):
            lines.append(f"URL: {data['url']}")
        if data.get("title"):
            lines.append(f"页面标题: {data['title']}")
        if data.get("headings"):
            lines.append("页面内标题:")
            for h in data["headings"][:25]:
                lines.append(f"  - {h}")
        if data.get("news_items"):
            lines.append("新闻/更新条目:")
            for item in data["news_items"][:12]:
                lines.append(f"  - {item[:250]}")

    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... (已截断)"
    return text


def call_deepseek(api_key, system_prompt, user_prompt, temperature=0.3):
    """调用 DeepSeek API，返回纯文本回复"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": 8192,
    }
    resp = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def extract_json_from_response(text):
    """从 AI 回复中提取 JSON 对象"""
    # 优先匹配 ```json ... ```
    match = re.search(r"```json\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    # 其次匹配 ``` ... ```
    match = re.search(r"```\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    # 最后尝试直接找 { ... }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])
    raise ValueError("无法从 AI 回复中提取 JSON")


def validate_structure(old, new, path=""):
    """
    验证新 JSON 结构与旧 JSON 一致（只允许 value 变化，不允许 key 变化）。
    列表长度可以变（增减条目），但每个条目的 key 集合必须一致。
    返回 (is_valid, errors)
    """
    errors = []

    if isinstance(old, Mapping) and isinstance(new, Mapping):
        old_keys = set(old.keys())
        new_keys = set(new.keys())
        if old_keys != new_keys:
            added = new_keys - old_keys
            removed = old_keys - new_keys
            if added:
                errors.append(f"{path or '根'}: 新增了 key {added}")
            if removed:
                errors.append(f"{path or '根'}: 删除了 key {removed}")
            return False, errors
        for k in old:
            p = f"{path}.{k}" if path else k
            valid, errs = validate_structure(old[k], new[k], p)
            errors.extend(errs)

    elif isinstance(old, list) and isinstance(new, list):
        # 列表长度可变；条目可以有些可选 key（如 done 只在部分条目出现）
        # 策略：用所有旧条目的 key 并集作为允许集合，不允许引入新 key，也不允许全部删除某 key
        if old and new:
            all_old_keys = set()
            for item in old:
                if isinstance(item, Mapping):
                    all_old_keys.update(item.keys())
            all_new_keys = set()
            for item in new:
                if isinstance(item, Mapping):
                    all_new_keys.update(item.keys())
            added = all_new_keys - all_old_keys
            if added:
                errors.append(f"{path}: 列表条目新增了 key {added}")
            removed = all_old_keys - all_new_keys
            if removed:
                errors.append(f"{path}: 列表条目删除了 key {removed}")
            # 检查每个新条目没有引入旧列表中不存在的 key
            for i, item in enumerate(new):
                if isinstance(item, Mapping):
                    bad = set(item.keys()) - all_old_keys
                    if bad:
                        errors.append(f"{path}[{i}]: 新增了 key {bad}")

    # 标量类型不严格检查（str/int/float/bool 可以互转，因为大部分值是字符串）

    return len(errors) == 0, errors


def compute_diff(old, new, path=""):
    """递归计算两个 JSON 之间的差异，返回差异列表"""
    diffs = []

    if isinstance(old, Mapping) and isinstance(new, Mapping):
        for k in old:
            p = f"{path}.{k}" if path else k
            if k in new:
                diffs.extend(compute_diff(old[k], new[k], p))
            else:
                diffs.append({"path": p, "old": old[k], "new": "(已删除)"})

    elif isinstance(old, list) and isinstance(new, list):
        max_len = max(len(old), len(new))
        for i in range(max_len):
            p = f"{path}[{i}]"
            if i < len(old) and i < len(new):
                diffs.extend(compute_diff(old[i], new[i], p))
            elif i < len(old):
                diffs.append({"path": p, "old": old[i], "new": "(已删除)"})
            else:
                diffs.append({"path": p, "old": "(新增)", "new": new[i]})

    else:
        if old != new:
            diffs.append({"path": path, "old": old, "new": new})

    return diffs


def update_meta_timestamp(data):
    """更新 meta.updated 时间戳"""
    if isinstance(data, Mapping) and "meta" in data:
        if isinstance(data["meta"], Mapping):
            data["meta"]["updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")


def update_board(board_key, dry_run=False):
    """更新单个板块的 JSON"""
    board = BOARDS[board_key]
    json_file = board["json_file"]

    print(f"\n{'─' * 50}")
    print(f"板块: {board_key} ({board['desc']})")
    print(f"{'─' * 50}")

    # 1. 查找快照
    snapshots_text = []
    found = 0
    for prefix in board["snapshots"]:
        snap_file = find_latest_snapshot(prefix)
        if snap_file:
            snapshots_text.append(format_snapshot(snap_file))
            found += 1
            print(f"  快照: {snap_file.name}")
        else:
            print(f"  未找到快照: {prefix}")

    if found == 0:
        print(f"  跳过（无快照）")
        return False

    # 2. 加载当前 JSON
    current_data = load_json(json_file)
    current_json_str = json.dumps(current_data, ensure_ascii=False, indent=2)

    # 3. 构建 Prompt
    system_prompt = f"""你是"钛星"科技新闻网站的数据编辑。根据最新抓取的网页快照，更新网站的 JSON 数据文件。

## 严格规则（必须遵守）
1. **只改 value，绝对不动 key 和 JSON 结构**
2. 不能新增、删除、重命名任何 key
3. 时间线条目可以增减（添加新事件、更新已有事件、移除过时事件），但每条的字段（key 集合）必须和原来一致
4. 没有新数据的字段保持原值不变
5. 亮点数字用"数字+单位"格式（如"75%"、"1024卡"、"3.5亿℃"）
6. 描述用简洁中文，突出关键数字和进展，一句话说清
7. 保留 HTML 标签不动（<span class='unit'>%</span>、<em>、<strong> 等）
8. 日期格式与现有格式保持一致
9. 如果快照中没有比当前数据更新的信息，返回原 JSON 不变

## 本板块说明
{board['desc']}
{board['hint']}

## 输出格式
输出完整的更新后 JSON，用 ```json 和 ``` 包裹。"""

    user_prompt = f"""## 当前 JSON 数据

```json
{current_json_str}
```

## 最新抓取的网页快照

{chr(10).join(snapshots_text)}

## 任务
对比快照和当前数据，找出有实质变化的信息，更新对应字段。
如果快照内容过时或无新信息，保持原值。
只输出更新后的完整 JSON，用 ```json 包裹。"""

    # 4. 调用 DeepSeek API
    api_key = get_api_key()
    print(f"  调用 DeepSeek API ...")

    try:
        response = call_deepseek(api_key, system_prompt, user_prompt)
    except Exception as e:
        print(f"  API 调用失败: {e}")
        return False

    # 5. 提取 JSON
    try:
        new_data = extract_json_from_response(response)
    except Exception as e:
        print(f"  JSON 解析失败: {e}")
        print(f"  AI 回复前 300 字: {response[:300]}")
        return False

    # 6. 验证结构
    is_valid, errors = validate_structure(current_data, new_data)
    if not is_valid:
        print(f"  结构验证失败（key 被改动），未写入:")
        for err in errors[:10]:
            print(f"    {err}")
        return False

    # 7. 计算差异
    diffs = compute_diff(current_data, new_data)

    if not diffs:
        print(f"  无变化（快照中没有新数据）")
        return True

    print(f"  检测到 {len(diffs)} 处变更:")
    for d in diffs:
        old_str = str(d["old"])
        new_str = str(d["new"])
        # 截断过长的值
        if len(old_str) > 80:
            old_str = old_str[:80] + "..."
        if len(new_str) > 80:
            new_str = new_str[:80] + "..."
        print(f"    {d['path']}")
        print(f"      旧: {old_str}")
        print(f"      新: {new_str}")

    # 8. 写入或 dry-run
    if dry_run:
        print(f"  [dry-run] 未写入文件")
    else:
        backup = backup_json(json_file)
        update_meta_timestamp(new_data)
        save_json(json_file, new_data)
        if backup:
            print(f"  备份: {backup.name}")
        print(f"  已写入 {json_file}")

    return True


# ============ 主入口 ============

def main():
    # 解析参数
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = set(a for a in sys.argv[1:] if a.startswith("--"))

    dry_run = "--dry-run" in flags

    print("=" * 60)
    print(f"钛星 AI 数据解读 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"模式: {'dry-run（只看不写）' if dry_run else '正式（写入 JSON）'}")
    print("=" * 60)

    # 确定要处理的板块
    if args:
        boards_to_run = []
        for arg in args:
            if arg in BOARDS:
                boards_to_run.append(arg)
            else:
                print(f"未知板块: {arg}")
                print(f"可选: {', '.join(BOARDS.keys())}")
                sys.exit(1)
    else:
        boards_to_run = list(BOARDS.keys())

    # 检查快照目录
    if not SNAPSHOT_DIR.exists():
        print(f"\n快照目录不存在: {SNAPSHOT_DIR}")
        print(f"请先运行: python fetch_data.py")
        sys.exit(1)

    # 逐个处理板块
    success = 0
    fail = 0
    for board_key in boards_to_run:
        try:
            if update_board(board_key, dry_run=dry_run):
                success += 1
            else:
                fail += 1
        except Exception as e:
            print(f"  异常: {e}")
            fail += 1

    # 汇总
    print(f"\n{'=' * 60}")
    print(f"完成: {success} 成功, {fail} 失败")
    if dry_run:
        print(f"dry-run 模式，JSON 文件未修改")
        print(f"确认无误后去掉 --dry-run 重新运行")
    else:
        print(f"已更新的 JSON 在 data/ 目录下")
        print(f"备份在 data/_backups/ 目录下")
        print(f"后续: git add -A && git commit -m 'AI更新数据' && git push")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()

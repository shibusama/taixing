#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
静态资源版本号升级工具

改完 css/js 文件后跑一下，自动把所有页面里的静态资源版本号（?v=YYYYMMDD）
升一档，强制浏览器/CDN 拉新文件，避免缓存导致部署后不显示改动。

用法：
    python scripts/bump_version.py            # 自动升到最新版本号
    python scripts/bump_version.py --check    # 只查看当前各页版本号，不修改
    python scripts/bump_version.py --set 20260820   # 手动指定版本号

特点：
    - 用 Python 读写 UTF-8（无 BOM），避免 PowerShell Set-Content 编码坑
    - 幂等：重复跑同一日期不会重复改（已经是新值就跳过）
    - 只改 pages/*.html 里的 ?v=YYYYMMDD，不动其他内容
"""
import argparse
import re
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = PROJECT_ROOT / "pages"
VERSION_RE = re.compile(r"\?v=(\d{8})")  # ?v=YYYYMMDD


def find_current_versions():
    """返回 {页面: [版本号字符串, ...]}"""
    result = {}
    for f in sorted(PAGES_DIR.glob("*.html")):
        content = f.read_text(encoding="utf-8")
        vers = VERSION_RE.findall(content)
        if vers:
            result[f.name] = sorted(set(vers))
    return result


def compute_next_version(current_max: str, today_str: str) -> str:
    """新版本号：今天日期 > 当前最大 → 用今天；否则当前最大 +1（避免重复）"""
    today_int = int(today_str)
    cur_int = int(current_max)
    if today_int > cur_int:
        return today_str
    # 今天 <= 当前最大 → 当前最大 +1
    return str(cur_int + 1)


def bump(target_version: str):
    """把所有页面的版本号替换成 target_version"""
    changed = []
    total = 0
    for f in sorted(PAGES_DIR.glob("*.html")):
        content = f.read_text(encoding="utf-8")
        new_content = VERSION_RE.sub(f"?v={target_version}", content)
        if new_content != content:
            n = len(VERSION_RE.findall(content))
            f.write_text(new_content, encoding="utf-8")  # UTF-8 无 BOM
            changed.append((f.name, n))
            total += n
    return changed, total


def main():
    parser = argparse.ArgumentParser(description="升级静态资源版本号")
    parser.add_argument("--check", action="store_true", help="只查看当前版本号，不修改")
    parser.add_argument("--set", dest="set_version", help="手动指定版本号，如 --set 20260820")
    args = parser.parse_args()

    current = find_current_versions()

    if args.check:
        if not current:
            print("没有找到任何 ?v=YYYYMMDD 版本号引用")
            return
        all_vers = sorted({v for vers in current.values() for v in vers})
        print(f"当前版本号: {all_vers}")
        for name, vers in current.items():
            print(f"  {name}: {vers}")
        return

    if not current:
        print("没有找到任何 ?v=YYYYMMDD 版本号引用，无需升级")
        return

    all_vers = [v for vers in current.values() for v in vers]
    current_max = max(all_vers)
    today_str = datetime.now().strftime("%Y%m%d")

    if args.set_version:
        # 手动指定：校验格式
        if not re.fullmatch(r"\d{8}", args.set_version):
            print(f"❌ 版本号格式错误：{args.set_version}（应为 YYYYMMDD，如 20260820）")
            return
        target = args.set_version
    else:
        target = compute_next_version(current_max, today_str)

    print(f"当前最大版本号: v{current_max}")
    print(f"新版本号:       v{target}")
    if target == current_max:
        print("（已是最新，无需更改）")
        return

    changed, total = bump(target)
    print(f"\n更新 {len(changed)} 个文件，共 {total} 处:")
    for name, n in changed:
        print(f"  {name}: {n} 处")
    print(f"\n✅ 完成。git add pages/*.html && git commit 后推送即可。")


if __name__ == "__main__":
    main()

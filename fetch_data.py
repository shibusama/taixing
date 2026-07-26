#!/usr/bin/env python3
"""
钛星网站数据抓取脚本
从一手源头抓取最新数据，自动更新可自动化的 JSON 字段，
其余数据保存原始快照供人工/AI解读后更新。

用法：
    python fetch_data.py           # 抓取全部数据源
    python fetch_data.py --finance # 只抓汇率/美联储
    python fetch_data.py --rocket  # 只抓火箭发射
    python fetch_data.py --scrape  # 只抓网页快照

依赖：pip install requests beautifulsoup4 lxml
"""

import json
import os
import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pathlib import Path

# ============ 路径配置 ============
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SNAPSHOT_DIR = DATA_DIR / "_snapshots"  # 原始快照目录

# ============ 工具函数 ============

def load_json(filename):
    """加载 JSON 文件"""
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filename, data):
    """保存 JSON 文件（保持 UTF-8 + 缩进）"""
    with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def update_meta(data):
    """更新 meta 时间戳"""
    if "meta" in data:
        data["meta"]["updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")

def fetch_json(url, params=None, timeout=10):
    """获取 JSON API"""
    resp = requests.get(url, params=params, timeout=timeout,
                        headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.json()

def fetch_html(url, timeout=10):
    """获取网页 HTML"""
    resp = requests.get(url, timeout=timeout,
                        headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text

def save_snapshot(name, content):
    """保存原始快照到 _snapshots/ 目录"""
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{name}_{ts}.json"
    with open(SNAPSHOT_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
    return filename

# ============ 1. 汇率数据 (finance.json) ============

def fetch_exchange_rates():
    """
    数据源：Frankfurter API（欧洲央行数据，免费无 key）
    文档：https://www.frankfurter.app/docs/
    """
    print("\n[1] 抓取汇率数据 (Frankfurter API / ECB)...")

    try:
        # 获取最新汇率
        latest = fetch_json(
            "https://api.frankfurter.app/latest",
            params={"from": "USD", "to": "JPY,CNY,EUR,GBP,CHF"}
        )
        rates = latest.get("rates", {})
        date = latest.get("date", "")

        # 获取昨日汇率（用于计算涨跌）
        yesterday = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        try:
            prev = fetch_json(f"https://api.frankfurter.app/{yesterday}",
                              params={"from": "USD", "to": "JPY"})
            prev_jpy = prev.get("rates", {}).get("JPY", rates.get("JPY"))
        except:
            prev_jpy = rates.get("JPY")

        jpy = rates.get("JPY")
        if not jpy:
            print("  [汇率] 未获取到 JPY 数据，跳过")
            return

        change_pct = ((jpy - prev_jpy) / prev_jpy * 100) if prev_jpy else 0
        print(f"  USD/JPY = {jpy:.2f} (前值 {prev_jpy:.2f}, {'+' if change_pct>=0 else ''}{change_pct:.2f}%)")

        # 获取近1个月走势
        end_date = datetime.strptime(date, "%Y-%m-%d")
        start_date = end_date - timedelta(days=30)
        try:
            monthly = fetch_json(
                f"https://api.frankfurter.app/{start_date.strftime('%Y-%m-%d')}..{date}",
                params={"from": "USD", "to": "JPY"}
            )
            monthly_rates = monthly.get("rates", {})
            all_values = [v["JPY"] for v in monthly_rates.values() if "JPY" in v]
            month_high = max(all_values) if all_values else jpy
            month_low = min(all_values) if all_values else jpy
        except:
            month_high = month_low = jpy

        # 更新 finance.json
        finance = load_json("finance.json")

        # fx_highlights
        finance["fx_highlights"][0]["num"] = f"{jpy:.2f}"
        now_cn = datetime.now()
        finance["fx_highlights"][0]["sub"] = f"{now_cn.month}月{now_cn.day:02d}日实时"
        finance["fx_highlights"][1]["num"] = f"{month_high:.2f}"
        finance["fx_highlights"][2]["num"] = f"{month_low:.2f}"

        # 年涨幅
        try:
            year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            year_data = fetch_json(f"https://api.frankfurter.app/{year_ago}",
                                   params={"from": "USD", "to": "JPY"})
            year_jpy = year_data.get("rates", {}).get("JPY", jpy)
            year_change = ((jpy - year_jpy) / year_jpy * 100)
            finance["fx_highlights"][3]["num"] = f"{'+' if year_change>=0 else ''}{year_change:.2f}<span class='unit'>%</span>"
        except:
            pass

        # fx_rates 当日行
        sign = "+" if change_pct >= 0 else ""
        finance["fx_rates"]["grid"][0]["v"] = f"{jpy:.3f} <em>{sign}{change_pct:.2f}%</em>"

        # 央行利率表也更新汇率
        update_meta(finance)
        save_json("finance.json", finance)
        print(f"  [汇率] finance.json 已更新 ✓")

        # 同时更新央行利率表中的其他汇率
        cb_rates = {
            "ECB": rates.get("EUR"),
            "BOE": rates.get("GBP"),
            "SNB": rates.get("CHF"),
        }
        print(f"  交叉汇率: EUR/USD={cb_rates['ECB']}, GBP/USD={cb_rates['BOE']}, CHF/USD={cb_rates['SNB']}")

    except Exception as e:
        print(f"  [汇率] 抓取失败: {e}")

# ============ 2. 美联储利率 (finance.json) ============

def fetch_fed_rate():
    """
    数据源：FRED API（圣路易斯联储，免费需 key）
    无 key 时尝试抓取 FRED 网页
    """
    print("\n[2] 抓取美联储利率 (FRED)...")

    FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

    try:
        if FRED_API_KEY:
            # 有 API key：直接获取数据
            data = fetch_json(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    "series_id": "FEDFUNDS",
                    "api_key": FRED_API_KEY,
                    "file_type": "json",
                    "limit": 1,
                    "sort_order": "desc"
                }
            )
            obs = data.get("observations", [{}])[0]
            rate = obs.get("value", "")
            date = obs.get("date", "")
            print(f"  美联储基金利率: {rate}% (截至 {date})")
        else:
            # 无 key：抓取 FRED RSS
            try:
                html = fetch_html("https://fred.stlouisfed.org/series/FEDFUNDS")
                soup = BeautifulSoup(html, "lxml")
                # 尝试从页面提取最新值
                title = soup.find("title")
                print(f"  [美联储] 无 FRED_API_KEY，建议设置后获取精确数据")
                print(f"  获取 key: https://fred.stlouisfed.org/docs/api/api_key.html")
                print(f"  设置方式: export FRED_API_KEY=你的key")
            except Exception as e:
                print(f"  [美联储] 抓取网页失败: {e}")

    except Exception as e:
        print(f"  [美联储] 抓取失败: {e}")

# ============ 3. 火箭发射日历 (rocket.json 参考) ============

def fetch_rocket_launches():
    """
    数据源：Launch Library 2 API（免费无 key）
    文档：https://ll.thespacedevs.com/2.2.0/docs/
    """
    print("\n[3] 抓取火箭发射日历 (Launch Library 2)...")

    try:
        data = fetch_json(
            "https://ll.thespacedevs.com/2.2.0/launch/upcoming/",
            params={"limit": 30, "ordering": "net"}
        )
        launches = data.get("results", [])

        # 筛选关注的火箭公司
        WATCH_LIST = ["SpaceX", "Blue Origin", "Rocket Lab", "CASC", "ExPace",
                       "LandSpace", "Galactic Energy", "Space Pioneer", "iSpace"]

        filtered = []
        for l in launches:
            agency = l.get("launch_service_provider", {}).get("name", "")
            if any(w.lower() in agency.lower() for w in WATCH_LIST) or l.get("rocket", {}):
                filtered.append({
                    "name": l.get("name", ""),
                    "date": l.get("net", ""),
                    "agency": agency,
                    "rocket": l.get("rocket", {}).get("configuration", {}).get("name", ""),
                    "pad": l.get("pad", {}).get("name", "") if l.get("pad") else "",
                    "location": l.get("pad", {}).get("location", {}).get("name", "") if l.get("pad") else "",
                    "status": l.get("status", {}).get("name", "") if l.get("status") else "",
                    "mission": l.get("mission", {}).get("name", "") if l.get("mission") else "",
                    "description": l.get("mission", {}).get("description", "")[:200] if l.get("mission") else ""
                })

        snap_file = save_snapshot("rocket_launches", filtered)
        print(f"  获取 {len(launches)} 条即将发射记录，筛选后 {len(filtered)} 条")
        print(f"  快照已保存: data/_snapshots/{snap_file}")

        # 打印近期发射
        for l in filtered[:10]:
            print(f"    {l['date'][:10]} | {l['agency']:<20} | {l['name'][:50]}")

    except Exception as e:
        print(f"  [火箭] 抓取失败: {e}")

# ============ 4. 网页快照抓取（供 AI 解读）============

def scrape_sources():
    """抓取各板块一手源头网页，保存快照供后续解读"""

    sources = [
        # 可回收火箭
        ("spacex_launches", "https://www.spacex.com/launches/"),
        ("blue_origin", "https://www.blueorigin.com/news"),
        ("rocket_lab", "https://www.rocketlabusa.com/updates/"),

        # 中美登月
        ("nasa_artemis", "https://www.nasa.gov/mission/artemis/"),

        # 可控核聚变
        ("iter_newsline", "https://www.iter.org/newsline"),
        ("cfs_commonwealth", "https://cfs.energy/news-and-media"),
        ("asipp_news", "http://www.ipp.cas.cn/xwdt/"),

        # 中国半导体
        ("smic_news", "https://www.smics.com/en/site/smics/NewsList"),
        ("smee_news", "https://www.smee.com.cn/news/list.html"),

        # 中国科技 AI
        ("deepseek_blog", "https://api-docs.deepseek.com/news"),
        ("moonshot_blog", "https://www.moonshot.cn/"),

        # 大工程
        ("china_railway", "https://www.china-railway.com.cn/"),

        # 科技资本
        ("anthropic_news", "https://www.anthropic.com/news"),
        ("openai_blog", "https://openai.com/blog/"),
    ]

    print(f"\n[4] 抓取网页快照（{len(sources)} 个源头）...")

    success = 0
    failed = 0

    for name, url in sources:
        try:
            html = fetch_html(url, timeout=20)
            soup = BeautifulSoup(html, "lxml")

            # 提取标题和文本摘要
            title = soup.find("title")
            title_text = title.get_text(strip=True) if title else ""

            # 提取所有标题标签
            headings = []
            for tag in ["h1", "h2", "h3"]:
                for h in soup.find_all(tag):
                    text = h.get_text(strip=True)
                    if text and len(text) < 200:
                        headings.append(text)

            # 提取新闻列表项（通用启发式）
            news_items = []
            for article in soup.find_all(["article", "div"], class_=lambda c: c and any(
                w in str(c).lower() for w in ["news", "post", "update", "article", "card", "item"]
            )):
                text = article.get_text(strip=True)[:300]
                if text:
                    news_items.append(text)

            snapshot = {
                "url": url,
                "title": title_text,
                "headings": headings[:30],
                "news_items": news_items[:20],
                "fetched_at": datetime.now().isoformat(),
            }

            snap_file = save_snapshot(name, snapshot)
            print(f"  ✓ {name:<25} | {title_text[:50]}")
            success += 1

        except Exception as e:
            print(f"  ✗ {name:<25} | {str(e)[:60]}")
            failed += 1

    print(f"\n  快照结果: {success} 成功, {failed} 失败")
    print(f"  快照目录: data/_snapshots/")

# ============ 5. 生成抓取报告 ============

def generate_report():
    """生成抓取摘要报告"""
    print("\n" + "=" * 60)
    print("抓取报告摘要")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"快照目录: {DATA_DIR / '_snapshots'}")
    print()
    print("自动更新的 JSON 文件:")
    print("  - finance.json (汇率数据)")
    print()
    print("需要人工/AI解读后更新的文件:")
    print("  - rocket.json (参考 _snapshots/rocket_launches_*.json)")
    print("  - moon.json (参考 _snapshots/nasa_artemis_*.json)")
    print("  - fusion.json (参考 _snapshots/iter_*.json, cfs_*.json)")
    print("  - semiconductor.json (参考 _snapshots/smic_*.json, smee_*.json)")
    print("  - china-tech.json (参考 _snapshots/deepseek_*.json, moonshot_*.json)")
    print("  - mega-projects.json (参考 _snapshots/china_railway_*.json)")
    print()
    print("提示: 将快照文件发给小布，由 AI 解读后更新对应 JSON")
    print("=" * 60)

# ============ 主入口 ============

def main():
    # 确保快照目录存在
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    args = set(sys.argv[1:])

    print("=" * 60)
    print(f"钛星数据抓取脚本 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # 默认运行全部
    run_all = not args or "--all" in args

    if run_all or "--finance" in args:
        fetch_exchange_rates()
        fetch_fed_rate()

    if run_all or "--rocket" in args:
        fetch_rocket_launches()

    if run_all or "--scrape" in args:
        scrape_sources()

    generate_report()

if __name__ == "__main__":
    main()

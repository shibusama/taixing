#!/usr/bin/env python3
"""
钛星网站数据爬虫脚本
每家数据源单独写解析规则，提取结构化数据（标题、日期、摘要）。

用法：
    python fetch_data.py               # 全部抓取
    python fetch_data.py --finance     # 只抓汇率
    python fetch_data.py --rocket      # 只抓火箭发射+火箭公司新闻
    python fetch_data.py --fusion      # 只抓核聚变
    python fetch_data.py --semicon     # 只抓半导体
    python fetch_data.py --ai          # 只抓AI公司
    python fetch_data.py --mega        # 只抓大工程
    python fetch_data.py --report      # 只生成报告

依赖：pip install requests beautifulsoup4 lxml
"""

import json
import os
import re
import sys
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pathlib import Path

# curl_cffi 用于绕过 TLS 指纹检测（中芯/OpenAI 等）
try:
    from curl_cffi import requests as cffi_requests
    HAS_CFFI = True
except ImportError:
    HAS_CFFI = False

# 抑制 SSL 警告
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============ 路径配置 ============
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = DATA_DIR / "_reports"

# ============ 通用工具 ============

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
}

def load_json(filename):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filename, data):
    with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def update_meta(data):
    if "meta" in data:
        data["meta"]["updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")

def fetch_html(url, timeout=20):
    resp = requests.get(url, timeout=timeout, headers=HEADERS, verify=False)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text

def fetch_html_cffi(url, timeout=20):
    """用 curl_cffi 伪装浏览器 TLS 指纹，绕过 Apache/WAF 的 403"""
    if not HAS_CFFI:
        raise RuntimeError("curl_cffi 未安装，请运行: pip install curl_cffi")
    resp = cffi_requests.get(url, impersonate="chrome", timeout=timeout, verify=False)
    resp.raise_for_status()
    return resp.text

def fetch_json(url, params=None, timeout=15):
    resp = requests.get(url, params=params, timeout=timeout, headers=HEADERS, verify=False)
    resp.raise_for_status()
    return resp.json()

def parse_date(text):
    """尝试多种日期格式解析，返回 YYYY-MM-DD"""
    text = text.strip()
    formats = [
        "%Y-%m-%d", "%Y/%m/%d",
        "%B %d, %Y", "%b %d, %Y",
        "%B %d %Y", "%b %d %Y",
        "%Y年%m月%d日", "%Y.%m.%d",
        "%d %B %Y", "%d %b %Y",
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text[:20], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    # 尝试从文本中提取日期
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
    if m:
        return m.group(0)
    m = re.search(r'(\w{3,9})\s+(\d{1,2}),?\s*(\d{4})', text)
    if m:
        try:
            return datetime.strptime(m.group(0).replace(",", ""), "%B %d %Y").strftime("%Y-%m-%d")
        except ValueError:
            try:
                return datetime.strptime(m.group(0).replace(",", ""), "%b %d %Y").strftime("%Y-%m-%d")
            except ValueError:
                pass
    return text[:30]  # 解析不了就返回原文截断


# ============ 汇率数据 (finance.json 自动写入) ============

def crawl_exchange_rates():
    """汇率 → 自动写入 finance.json"""
    print("\n[汇率] 抓取 Frankfurter API (ECB)...")
    try:
        latest = fetch_json("https://api.frankfurter.app/latest",
                            params={"from": "USD", "to": "JPY,CNY,EUR,GBP,CHF"})
        rates = latest.get("rates", {})
        date = latest.get("date", "")
        jpy = rates.get("JPY")
        if not jpy:
            print("  [汇率] 未获取到 JPY，跳过")
            return None

        # 昨日汇率
        prev_jpy = jpy
        try:
            yesterday = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
            prev = fetch_json(f"https://api.frankfurter.app/{yesterday}",
                              params={"from": "USD", "to": "JPY"})
            prev_jpy = prev.get("rates", {}).get("JPY", jpy)
        except:
            pass

        change_pct = ((jpy - prev_jpy) / prev_jpy * 100) if prev_jpy else 0
        print(f"  USD/JPY = {jpy:.2f} ({'+' if change_pct>=0 else ''}{change_pct:.2f}%)")

        # 写入 finance.json
        finance = load_json("finance.json")
        now_cn = datetime.now()
        finance["fx_highlights"][0]["num"] = f"{jpy:.2f}"
        finance["fx_highlights"][0]["sub"] = f"{now_cn.month}月{now_cn.day:02d}日实时"

        # 月高低
        try:
            end_date = datetime.strptime(date, "%Y-%m-%d")
            start_date = end_date - timedelta(days=30)
            monthly = fetch_json(
                f"https://api.frankfurter.app/{start_date.strftime('%Y-%m-%d')}..{date}",
                params={"from": "USD", "to": "JPY"})
            vals = [v["JPY"] for v in monthly.get("rates", {}).values() if "JPY" in v]
            if vals:
                finance["fx_highlights"][1]["num"] = f"{max(vals):.2f}"
                finance["fx_highlights"][2]["num"] = f"{min(vals):.2f}"
        except:
            pass

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

        # 当日汇率行
        sign = "+" if change_pct >= 0 else ""
        finance["fx_rates"]["grid"][0]["v"] = f"{jpy:.3f} <em>{sign}{change_pct:.2f}%</em>"
        update_meta(finance)
        save_json("finance.json", finance)
        print(f"  [汇率] finance.json 已更新 ✓")
        return {"usd_jpy": jpy, "change_pct": change_pct}
    except Exception as e:
        print(f"  [汇率] 失败: {e}")
        return None


# ============ 火箭发射日历 (Launch Library 2 API) ============

def crawl_rocket_launches():
    """火箭发射日历 → 结构化数据"""
    print("\n[火箭发射] 抓取 Launch Library 2 API...")
    try:
        data = fetch_json("https://ll.thespacedevs.com/2.2.0/launch/upcoming/",
                          params={"limit": 50, "ordering": "net"})
        launches = data.get("results", [])
        WATCH = ["SpaceX", "Blue Origin", "Rocket Lab", "CASC",
                 "LandSpace", "Galactic Energy", "Space Pioneer", "iSpace",
                 "ExPace", "Isar Aerospace", "Rocket Factory", "Firefly"]

        items = []
        for l in launches:
            agency = l.get("launch_service_provider", {}).get("name", "")
            if not any(w.lower() in agency.lower() for w in WATCH):
                continue
            items.append({
                "source": "launch_library_2",
                "board": "rocket",
                "title": l.get("name", ""),
                "date": l.get("net", "")[:10],
                "agency": agency,
                "rocket": l.get("rocket", {}).get("configuration", {}).get("name", ""),
                "status": l.get("status", {}).get("name", "") if l.get("status") else "",
                "mission": l.get("mission", {}).get("name", "") if l.get("mission") else "",
                "summary": (l.get("mission", {}).get("description", "")[:200] if l.get("mission") else ""),
                "url": l.get("url", ""),
            })

        print(f"  获取 {len(items)} 条关注火箭发射")
        for item in items[:8]:
            print(f"    {item['date']} | {item['agency']:<12} | {item['title'][:50]}")
        return items
    except Exception as e:
        print(f"  [火箭发射] API失败: {e}")
        print(f"  [火箭发射] 尝试备用源 (SpaceLaunchNow)...")
        try:
            data = fetch_json("https://spacelaunchnow-prod-east.nyc3.digitaloceanspaces.com/launch/upcoming.json")
            launches = data.get("results", data if isinstance(data, list) else [])
            items = []
            for l in (launches[:50] if isinstance(launches, list) else []):
                agency = l.get("launch_service_provider", {}).get("name", "") if isinstance(l, dict) else ""
                items.append({
                    "source": "launch_library_2",
                    "board": "rocket",
                    "title": l.get("name", "") if isinstance(l, dict) else str(l),
                    "date": (l.get("net", "")[:10] if isinstance(l, dict) else ""),
                    "agency": agency,
                    "status": (l.get("status", {}).get("name", "") if isinstance(l, dict) and l.get("status") else ""),
                    "summary": "",
                    "url": "",
                })
            print(f"  备用源获取 {len(items)} 条")
            return items
        except Exception as e2:
            print(f"  [火箭发射] 备用源也失败: {e2}")
            return []


# ============ Blue Origin 新闻 ============

def crawl_blue_origin():
    """Blue Origin 官网新闻 → 日期+标题+摘要"""
    print("\n[Blue Origin] 抓取官网新闻...")
    try:
        html = fetch_html("https://www.blueorigin.com/news")
        soup = BeautifulSoup(html, "lxml")
        items = []

        # Blue Origin 页面可能 JS 渲染，但 headings 里有标题
        # 从快照看，h2/h3 里有文章标题
        skip_words = {"The Latest from Blue", "Space Systems", "Company",
                      "Press Inquiries", "Follow Blue Origin", "Subscribe",
                      "News", "Careers", "Sustainability"}

        # 策略1: 找所有 heading 里的文章标题
        for tag in ["h2", "h3", "h4"]:
            for h in soup.find_all(tag):
                title = h.get_text(strip=True)
                if not title or len(title) < 15 or title in skip_words:
                    continue
                if any(sw in title for sw in ["Blue Origin", "Subscribe", "Follow"]):
                    if len(title) < 30:
                        continue

                # 在 heading 附近找日期
                date_str = ""
                parent = h.find_parent()
                if parent:
                    text = parent.get_text(separator=" ")
                    date_match = re.search(
                        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})',
                        text)
                    if date_match:
                        date_str = parse_date(date_match.group(1))

                # 找链接
                link = h.find("a") or (parent.find("a") if parent else None)
                url = link.get("href", "") if link else ""
                if url and not url.startswith("http"):
                    url = "https://www.blueorigin.com" + url

                if not any(i["title"] == title for i in items):
                    items.append({
                        "source": "blue_origin",
                        "board": "rocket",
                        "title": title,
                        "date": date_str,
                        "summary": "",
                        "url": url or "https://www.blueorigin.com/news",
                    })

        # 策略2: 全文搜索日期+标题模式
        if len(items) < 3:
            all_text = soup.get_text(separator="\n")
            # 找 "Mon DD, YYYY" 后面跟着标题的模式
            pattern = re.compile(
                r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\s*(?:News)?\s*(.+?)(?:Read more|$)',
                re.MULTILINE)
            for m in pattern.finditer(all_text):
                date_str = parse_date(m.group(1))
                title = m.group(2).strip()[:150]
                if title and len(title) > 10 and not any(i["title"] == title for i in items):
                    items.append({
                        "source": "blue_origin",
                        "board": "rocket",
                        "title": title,
                        "date": date_str,
                        "summary": "",
                        "url": "https://www.blueorigin.com/news",
                    })

        print(f"  解析到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"    {item['date'] or '?':<12} | {item['title'][:60]}")
        return items
    except Exception as e:
        print(f"  [Blue Origin] 失败: {e}")
        return []


# ============ Rocket Lab 新闻 ============

def crawl_rocket_lab():
    """Rocket Lab 官网新闻 → 解析日期+标题"""
    print("\n[Rocket Lab] 抓取官网新闻...")
    try:
        html = fetch_html("https://www.rocketlabusa.com/updates/")
        soup = BeautifulSoup(html, "lxml")
        items = []

        # Rocket Lab 新闻格式: "July 7, 2026 Title Read more"
        # 尝试找到所有包含日期的文本块
        for elem in soup.find_all(["div", "article", "li", "p"]):
            text = elem.get_text(separator=" ", strip=True)
            if len(text) < 20:
                continue

            date_match = re.search(
                r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})',
                text)
            if not date_match:
                continue

            date_str = parse_date(date_match.group(1))
            # 标题 = 日期之后到 "Read more" 之前
            after_date = text[date_match.end():].strip()
            title = after_date.split("Read more")[0].strip()[:150]

            if title and not any(i["title"] == title for i in items):
                items.append({
                    "source": "rocket_lab",
                    "board": "rocket",
                    "title": title,
                    "date": date_str,
                    "summary": "",
                    "url": "https://www.rocketlabusa.com/updates/",
                })

        print(f"  解析到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"    {item['date']} | {item['title'][:60]}")
        return items
    except Exception as e:
        print(f"  [Rocket Lab] 失败: {e}")
        return []


# ============ SpaceX 新闻 (通过 API) ============

def crawl_spacex():
    """SpaceX 没有可抓的 HTML 新闻页（JS渲染），从 Launch Library API 提取"""
    print("\n[SpaceX] 通过 Launch Library API 提取最新发射...")
    try:
        data = fetch_json("https://ll.thespacedevs.com/2.2.0/launch/upcoming/",
                          params={"limit": 20, "ordering": "-net",
                                  "launch_service_provider": "SpaceX"})
        launches = data.get("results", [])
        # 也获取最近的过去发射
        past_data = fetch_json("https://ll.thespacedevs.com/2.2.0/launch/previous/",
                               params={"limit": 10, "ordering": "-net",
                                       "launch_service_provider": "SpaceX"})
        launches.extend(past_data.get("results", []))

        items = []
        for l in launches:
            items.append({
                "source": "spacex",
                "board": "rocket",
                "title": l.get("name", ""),
                "date": l.get("net", "")[:10],
                "agency": "SpaceX",
                "rocket": l.get("rocket", {}).get("configuration", {}).get("name", ""),
                "status": l.get("status", {}).get("name", "") if l.get("status") else "",
                "summary": (l.get("mission", {}).get("description", "")[:200] if l.get("mission") else ""),
                "url": l.get("url", ""),
            })

        print(f"  获取 {len(items)} 条 SpaceX 发射记录")
        for item in items[:5]:
            print(f"    {item['date']} | {item['status']:<20} | {item['title'][:50]}")
        return items
    except Exception as e:
        print(f"  [SpaceX] 失败: {e}")
        return []


# ============ ITER 新闻 ============

def crawl_iter():
    """ITER Newsline → 解析文章标题"""
    print("\n[ITER] 抓取 Newsline...")
    try:
        html = fetch_html("https://www.iter.org/newsline")
        soup = BeautifulSoup(html, "lxml")
        items = []

        # ITER 新闻列表中的文章标题
        # 从 headings 中提取（排除导航/页脚标题）
        skip_words = {"Newsline archive", "Subscribe to the newsletter", "2026", "2025", "2024",
                      "Home", "News & Media", "Newsroom"}

        for tag in ["h2", "h3", "h4"]:
            for h in soup.find_all(tag):
                title = h.get_text(strip=True)
                if not title or len(title) < 10 or title in skip_words:
                    continue
                if any(sw in title for sw in skip_words):
                    continue

                # 找相邻的日期
                parent = h.find_parent()
                date_str = ""
                if parent:
                    date_elem = parent.find(string=re.compile(r'\d{4}'))
                    if date_elem:
                        date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', date_elem)
                        if date_match:
                            date_str = parse_date(date_match.group(1))

                if not any(i["title"] == title for i in items):
                    items.append({
                        "source": "iter",
                        "board": "fusion",
                        "title": title,
                        "date": date_str,
                        "summary": "",
                        "url": "https://www.iter.org/newsline",
                    })

        print(f"  解析到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"    {item['date'] or '?':<12} | {item['title'][:60]}")
        return items
    except Exception as e:
        print(f"  [ITER] 失败: {e}")
        return []


# ============ CFS (Commonwealth Fusion Systems) 新闻 ============

def crawl_cfs():
    """CFS 官网新闻 → 解析标题"""
    print("\n[CFS] 抓取官网新闻...")
    try:
        html = fetch_html("https://cfs.energy/news-and-media")
        soup = BeautifulSoup(html, "lxml")
        items = []

        skip_words = {"CFS in the News", "Join the power movement", "Press",
                      "Commonwealth Fusion Systems"}

        for tag in ["h2", "h3", "h4", "h5"]:
            for h in soup.find_all(tag):
                title = h.get_text(strip=True)
                if not title or len(title) < 15 or title in skip_words:
                    continue

                # 找链接
                link = h.find("a")
                url = link.get("href", "") if link else ""
                if url and not url.startswith("http"):
                    url = "https://cfs.energy" + url

                if not any(i["title"] == title for i in items):
                    items.append({
                        "source": "cfs",
                        "board": "fusion",
                        "title": title,
                        "date": "",
                        "summary": "",
                        "url": url or "https://cfs.energy/news-and-media",
                    })

        print(f"  解析到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"    {item['title'][:70]}")
        return items
    except Exception as e:
        print(f"  [CFS] 失败: {e}")
        return []


# ============ ASIPP (中科院等离子体所) 新闻 ============

def crawl_asipp():
    """ASIPP 新闻 → 解析中文新闻标题"""
    print("\n[ASIPP] 抓取中科院等离子体所...")
    try:
        html = fetch_html("http://www.ipp.cas.cn/xwdt/")
        soup = BeautifulSoup(html, "lxml")
        items = []

        # 中国科研网站通常用 <a> 标签列表 + 日期
        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            if not title or len(title) < 8:
                continue
            # 排除导航链接
            if any(w in title for w in ["首页", "登录", "注册", "搜索", "更多", "English", "设为首页"]):
                continue

            # 找相邻日期
            parent = a.find_parent()
            date_str = ""
            if parent:
                date_text = parent.get_text()
                date_match = re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', date_text)
                if date_match:
                    date_str = parse_date(date_match.group(0).replace("年", "-").replace("月", "-").replace("/", "-"))

            href = a["href"]
            if href and not href.startswith("http"):
                href = "http://www.ipp.cas.cn" + href

            if date_str and not any(i["title"] == title for i in items):
                items.append({
                    "source": "asipp",
                    "board": "fusion",
                    "title": title,
                    "date": date_str,
                    "summary": "",
                    "url": href,
                })

        print(f"  解析到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"    {item['date']} | {item['title'][:50]}")
        return items
    except Exception as e:
        print(f"  [ASIPP] 失败: {e}")
        return []


# ============ NASA Artemis ============

def crawl_nasa_artemis():
    """NASA Artemis → 尝试 RSS"""
    print("\n[NASA] 抓取 Artemis 新闻...")
    try:
        # 尝试 NASA RSS
        html = fetch_html("https://www.nasa.gov/missions/artemis/")
        soup = BeautifulSoup(html, "lxml")
        items = []

        # NASA 网页通常有 article 或 div.card 结构
        for article in soup.find_all(["article", "div"], class_=lambda c: c and any(
            w in str(c).lower() for w in ["card", "article", "post", "news", "mission"]
        )):
            title_elem = article.find(["h2", "h3", "h4"])
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 10:
                continue

            # 日期
            date_str = ""
            time_elem = article.find("time")
            if time_elem:
                date_str = time_elem.get("datetime", "")[:10]
            if not date_str:
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', article.get_text())
                if date_match:
                    date_str = date_match.group(1)

            link = title_elem.find("a")
            url = link.get("href", "") if link else ""
            if url and not url.startswith("http"):
                url = "https://www.nasa.gov" + url

            if not any(i["title"] == title for i in items):
                items.append({
                    "source": "nasa_artemis",
                    "board": "moon",
                    "title": title,
                    "date": date_str,
                    "summary": article.get_text(strip=True)[:200],
                    "url": url,
                })

        print(f"  解析到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"    {item['date'] or '?':<12} | {item['title'][:60]}")
        return items
    except Exception as e:
        print(f"  [NASA] 失败: {e}")
        return []


# ============ Anthropic 新闻 ============

def crawl_anthropic():
    """Anthropic Newsroom → 解析标题+日期+分类"""
    print("\n[Anthropic] 抓取 Newsroom...")
    try:
        html = fetch_html("https://www.anthropic.com/news")
        soup = BeautifulSoup(html, "lxml")
        items = []

        # Anthropic 新闻格式: "Category Date Title Description"
        # 尝试找新闻卡片
        for article in soup.find_all(["article", "div"], class_=lambda c: c and any(
            w in str(c).lower() for w in ["news", "post", "card", "article", "item"]
        )):
            text = article.get_text(separator=" ", strip=True)
            if len(text) < 20:
                continue

            # 提取日期 (格式: Jul 24, 2026)
            date_match = re.search(r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})', text)
            date_str = parse_date(date_match.group(1)) if date_match else ""

            # 提取标题（通常是第一个 heading 或粗体文本）
            title = ""
            for tag in ["h2", "h3", "h4"]:
                h = article.find(tag)
                if h:
                    title = h.get_text(strip=True)
                    break

            # 如果没找到 heading，尝试从文本提取
            if not title and date_match:
                # 标题在日期之前或之后
                before_date = text[:date_match.start()].strip()
                after_date = text[date_match.end():].strip()
                # 优先用日期后的内容作为标题
                title = after_date.split(".")[0][:150] if after_date else before_date[:150]

            if title and not any(i["title"] == title for i in items):
                # 过滤描述性文本（完整句子被误当标题）
                words = title.split()
                if len(words) > 12 and not title[0].isupper():
                    continue
                if re.match(r'^[A-Z][a-z]+ \d+ is a ', title):
                    continue
                items.append({
                    "source": "anthropic",
                    "board": "ai",
                    "title": title,
                    "date": date_str,
                    "summary": text[:300],
                    "url": "https://www.anthropic.com/news",
                })

        print(f"  解析到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"    {item['date'] or '?':<12} | {item['title'][:60]}")
        return items
    except Exception as e:
        print(f"  [Anthropic] 失败: {e}")
        return []


# ============ DeepSeek 新闻 ============

def crawl_deepseek():
    """DeepSeek 新闻 → 解析 API 文档新闻页"""
    print("\n[DeepSeek] 抓取新闻...")
    try:
        urls = [
            "https://api-docs.deepseek.com/news",
            "https://api-docs.deepseek.com/zh-cn/news",
        ]
        html = None
        for url in urls:
            try:
                html = fetch_html(url)
                break
            except:
                continue

        if not html:
            print("  [DeepSeek] 无法访问新闻页")
            return []

        soup = BeautifulSoup(html, "lxml")
        items = []

        # DeepSeek 文档站新闻列表 — 过滤导航/页脚链接
        NAV_WORDS = {"english", "中文", "search", "quick start", "api", "docs",
                     "platform", "models", "pricing", "token", "rate limit",
                     "guides", "reference", "resources", "news", "other",
                     "skip to main content", "deepseek", "integration", "agent",
                     "logout", "login", "sign up", "about", "home",
                     "error codes", "thinking mode", "multi-round conversation",
                     "your first api call", "deepseek api docs",
                     "function calling", "json output", "faq",
                     "api key", "compatibility", "support"}

        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            if not title or len(title) < 8 or len(title) > 200:
                continue
            if title.lower() in NAV_WORDS:
                continue
            if any(w in title.lower() for w in ["skip to", "deepseek platform", "models & pricing",
                                                  "token & token", "rate limit", "api guides",
                                                  "api reference", "agent integrations",
                                                  "quick start", "other resources",
                                                  "error codes", "thinking mode",
                                                  "multi-round conversation", "your first api call",
                                                  "function calling", "json output",
                                                  "api key", "compatibility", "faq",
                                                  "deepseek api docs", "log out",
                                                  "sign in", "documentation"]):
                continue

            # 只保留看起来像新闻标题的链接（包含年份或日期或有实质内容）
            href = a["href"]
            if href and not href.startswith("http"):
                href = "https://api-docs.deepseek.com" + href

            if not any(i["title"] == title for i in items):
                items.append({
                    "source": "deepseek",
                    "board": "ai",
                    "title": title,
                    "date": "",
                    "summary": "",
                    "url": href,
                })

        # 如果文档站没抓到新闻，尝试 DeepSeek 主站
        if len(items) < 3:
            try:
                html2 = fetch_html("https://www.deepseek.com/")
                soup2 = BeautifulSoup(html2, "lxml")
                for a in soup2.find_all("a", href=True):
                    title = a.get_text(strip=True)
                    if not title or len(title) < 8 or len(title) > 150:
                        continue
                    if title.lower() in NAV_WORDS:
                        continue
                    href = a["href"]
                    if href and not href.startswith("http"):
                        href = "https://www.deepseek.com" + href
                    if not any(i["title"] == title for i in items):
                        items.append({
                            "source": "deepseek",
                            "board": "ai",
                            "title": title,
                            "date": "",
                            "summary": "",
                            "url": href,
                        })
            except:
                pass

        print(f"  解析到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"    {item['title'][:60]}")
        return items
    except Exception as e:
        print(f"  [DeepSeek] 失败: {e}")
        return []


# ============ Moonshot / Kimi 新闻 ============

def crawl_moonshot():
    """月之暗面官网 → 解析产品动态"""
    print("\n[Moonshot] 抓取官网动态...")
    try:
        html = fetch_html("https://www.moonshot.cn/")
        soup = BeautifulSoup(html, "lxml")
        items = []

        # Moonshot 格式: "2026-07-16Kimi K3" (日期紧跟标题)
        # 提取相邻日期之间的文本作为标题
        raw_text = soup.get_text()
        date_matches = list(re.finditer(r'\d{4}-\d{2}-\d{2}', raw_text))
        seen_titles = set()
        for i, d in enumerate(date_matches):
            date_str = d.group(0)
            start = d.end()
            end = date_matches[i + 1].start() if i + 1 < len(date_matches) else min(start + 80, len(raw_text))
            title = raw_text[start:end].strip()
            # 截到第一个中文
            title = re.split(r'[\u4e00-\u9fff]', title)[0].strip()
            if len(title) < 2 or len(title) > 50:
                continue
            if title not in seen_titles:
                seen_titles.add(title)
                items.append({
                    "source": "moonshot",
                    "board": "ai",
                    "title": title,
                    "date": date_str,
                    "summary": "",
                    "url": "https://www.moonshot.cn/",
                })

        print(f"  解析到 {len(items)} 条动态")
        for item in items[:5]:
            print(f"    {item['date']} | {item['title'][:50]}")
        return items
    except Exception as e:
        print(f"  [Moonshot] 失败: {e}")
        return []


# ============ OpenAI 新闻 ============

def crawl_openai():
    """OpenAI Blog → 解析文章标题（用 curl_cffi 绕过 Cloudflare）"""
    print("\n[OpenAI] 抓取 Blog...")
    try:
        # OpenAI 有 Cloudflare 保护，普通 requests 会被 403
        if HAS_CFFI:
            html = fetch_html_cffi("https://openai.com/blog/", timeout=30)
        else:
            html = fetch_html("https://openai.com/blog/", timeout=20)
        soup = BeautifulSoup(html, "lxml")
        items = []

        for article in soup.find_all(["article", "div"], class_=lambda c: c and any(
            w in str(c).lower() for w in ["post", "article", "card", "blog"]
        )):
            title_elem = article.find(["h2", "h3", "h4"])
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            date_str = ""
            time_elem = article.find("time")
            if time_elem:
                date_str = time_elem.get("datetime", "")[:10]

            link = title_elem.find("a")
            url = link.get("href", "") if link else ""
            if url and not url.startswith("http"):
                url = "https://openai.com" + url

            if not any(i["title"] == title for i in items):
                items.append({
                    "source": "openai",
                    "board": "ai",
                    "title": title,
                    "date": date_str,
                    "summary": "",
                    "url": url,
                })

        print(f"  解析到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"    {item['date'] or '?':<12} | {item['title'][:60]}")
        return items
    except Exception as e:
        print(f"  [OpenAI] 失败: {e}")
        return []


# ============ 中芯国际 (SMIC) 新闻 ============

def crawl_smic():
    """中芯国际官网新闻 — 用 curl_cffi 绕过 Apache 403"""
    print("\n[SMIC] 抓取中芯国际新闻...")
    try:
        # 中芯 Apache 服务器会检测 TLS 指纹，普通 requests 会被 403
        # 用 curl_cffi 伪装 Chrome 指纹
        if HAS_CFFI:
            html = fetch_html_cffi("https://www.smics.com/site/news", timeout=30)
        else:
            print("  [SMIC] 需要 curl_cffi，回退到普通 requests（可能403）")
            html = fetch_html("https://www.smics.com/site/news", timeout=30)
        
        soup = BeautifulSoup(html, "lxml")
        items = []
        seen = set()

        # 中芯新闻结构: <a href="/site/news_read/XXXX">标题</a> + 日期 + 摘要
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "news_read" not in href:
                continue
            title = a.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            if title in seen:
                continue
            seen.add(title)

            # 找日期和摘要（在父级或兄弟节点）
            parent = a.find_parent()
            date_str = ""
            summary = ""
            if parent:
                parent_text = parent.get_text(separator=" ", strip=True)
                date_match = re.search(r'(\d{4}-\d{1,2}-\d{1,2})', parent_text)
                if date_match:
                    date_str = date_match.group(1)
                # 摘要 = 标题之后的文本
                after_title = parent_text.split(title, 1)
                if len(after_title) > 1:
                    summary = after_title[1].strip()[:200]
                    # 去掉日期部分
                    summary = re.sub(r'^\d{4}-\d{1,2}-\d{1,2}\s*', '', summary)

            if not href.startswith("http"):
                href = "https://www.smics.com" + href

            items.append({
                "source": "smic",
                "board": "semicon",
                "title": title,
                "date": date_str,
                "summary": summary,
                "url": href,
            })

        print(f"  解析到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"    {item['date']} | {item['title'][:60]}")
        return items
    except Exception as e:
        print(f"  [SMIC] 失败: {e}")
        return []


# ============ 上海微电子 (SMEE) 新闻 ============

def crawl_smee():
    """上海微电子官网新闻"""
    print("\n[SMEE] 抓取上海微电子新闻...")
    try:
        html = fetch_html("https://www.smee.com.cn/")
        soup = BeautifulSoup(html, "lxml")
        items = []

        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            if any(w in title for w in ["首页", "登录", "English", "更多", "搜索"]):
                continue

            parent = a.find_parent()
            date_str = ""
            if parent:
                date_match = re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', parent.get_text())
                if date_match:
                    date_str = parse_date(date_match.group(0).replace("年", "-").replace("月", "-").replace("/", "-"))

            href = a["href"]
            if href and not href.startswith("http"):
                href = "https://www.smee.com.cn" + href

            if date_str and not any(i["title"] == title for i in items):
                items.append({
                    "source": "smee",
                    "board": "semicon",
                    "title": title,
                    "date": date_str,
                    "summary": "",
                    "url": href,
                })

        print(f"  解析到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"    {item['date']} | {item['title'][:50]}")
        return items
    except Exception as e:
        print(f"  [SMEE] 失败: {e}")
        return []


# ============ 国铁集团新闻 ============

def crawl_china_railway():
    """国铁集团官网新闻"""
    print("\n[国铁] 抓取国铁集团新闻...")
    try:
        html = fetch_html("https://www.china-railway.com.cn/")
        soup = BeautifulSoup(html, "lxml")
        items = []

        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            if not title or len(title) < 8:
                continue
            if any(w in title for w in ["首页", "登录", "English", "更多", "搜索", "网站地图"]):
                continue

            parent = a.find_parent()
            date_str = ""
            if parent:
                date_match = re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', parent.get_text())
                if date_match:
                    date_str = parse_date(date_match.group(0).replace("年", "-").replace("月", "-").replace("/", "-"))

            href = a["href"]
            if href and not href.startswith("http"):
                href = "https://www.china-railway.com.cn" + href

            if not any(i["title"] == title for i in items):
                items.append({
                    "source": "china_railway",
                    "board": "mega",
                    "title": title,
                    "date": date_str,
                    "summary": "",
                    "url": href,
                })

        print(f"  解析到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"    {item['date'] or '?':<12} | {item['title'][:50]}")
        return items
    except Exception as e:
        print(f"  [国铁] 失败: {e}")
        return []


# ============ 美联储利率 ============

def crawl_fed_rate():
    """美联储利率 → 从 FRED 或网页抓取"""
    print("\n[美联储] 抓取利率数据...")
    try:
        # 尝试 FRED API（如果有 key）
        fred_key = os.environ.get("FRED_API_KEY", "")
        if fred_key:
            data = fetch_json("https://api.stlouisfed.org/fred/series/observations",
                              params={"series_id": "FEDFUNDS", "api_key": fred_key,
                                      "file_type": "json", "limit": 1, "sort_order": "desc"})
            obs = data.get("observations", [{}])[0]
            rate = obs.get("value", "")
            date = obs.get("date", "")
            print(f"  美联储基金利率: {rate}% (截至 {date})")
            return {"rate": rate, "date": date}
        else:
            # 无 key，抓 FRED 网页
            html = fetch_html("https://fred.stlouisfed.org/series/FEDFUNDS")
            soup = BeautifulSoup(html, "lxml")
            # 从页面提取最新值
            value_elem = soup.find(class_=lambda c: c and "value" in str(c).lower())
            if value_elem:
                print(f"  美联储基金利率: {value_elem.get_text(strip=True)}")
            print("  提示: 设置 FRED_API_KEY 环境变量可获取精确数据")
            return None
    except Exception as e:
        print(f"  [美联储] 失败: {e}")
        return None


# ============ 报告生成 ============

def generate_report(all_items):
    """生成结构化爬取报告"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")

    # 按板块分组
    boards = {}
    for item in all_items:
        board = item.get("board", "other")
        if board not in boards:
            boards[board] = []
        boards[board].append(item)

    # 写 JSON 报告
    report = {
        "generated_at": datetime.now().isoformat(),
        "total_items": len(all_items),
        "by_board": {k: len(v) for k, v in boards.items()},
        "items": all_items,
    }

    report_file = REPORT_DIR / f"crawl_report_{ts}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 打印摘要
    print("\n" + "=" * 60)
    print("爬取报告")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总计: {len(all_items)} 条")
    print()
    for board, items in sorted(boards.items()):
        print(f"  [{board}] {len(items)} 条")
        for item in items[:3]:
            date = item.get("date", "?")
            title = item.get("title", "")[:55]
            print(f"    {date:<12} | {title}")
        if len(items) > 3:
            print(f"    ... 还有 {len(items)-3} 条")
    print()
    print(f"报告文件: {report_file}")
    print("=" * 60)

    return report_file


# ============ 主入口 ============

def main():
    args = set(sys.argv[1:])

    print("=" * 60)
    print(f"钛星数据爬虫 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    run_all = not args or "--all" in args
    all_items = []

    # --- 汇率（自动写入 JSON）---
    if run_all or "--finance" in args:
        crawl_exchange_rates()
        crawl_fed_rate()

    # --- 火箭板块 ---
    if run_all or "--rocket" in args:
        all_items += crawl_rocket_launches()
        time.sleep(1)
        all_items += crawl_spacex()
        time.sleep(1)
        all_items += crawl_blue_origin()
        time.sleep(1)
        all_items += crawl_rocket_lab()

    # --- 登月板块 ---
    if run_all or "--moon" in args:
        time.sleep(1)
        all_items += crawl_nasa_artemis()

    # --- 核聚变板块 ---
    if run_all or "--fusion" in args:
        time.sleep(1)
        all_items += crawl_iter()
        time.sleep(1)
        all_items += crawl_cfs()
        time.sleep(1)
        all_items += crawl_asipp()

    # --- 半导体板块 ---
    if run_all or "--semicon" in args:
        time.sleep(1)
        all_items += crawl_smic()
        time.sleep(1)
        all_items += crawl_smee()

    # --- AI 板块 ---
    if run_all or "--ai" in args:
        time.sleep(1)
        all_items += crawl_anthropic()
        time.sleep(1)
        all_items += crawl_deepseek()
        time.sleep(1)
        all_items += crawl_moonshot()
        time.sleep(1)
        all_items += crawl_openai()

    # --- 大工程板块 ---
    if run_all or "--mega" in args:
        time.sleep(1)
        all_items += crawl_china_railway()

    # --- 生成报告 ---
    if run_all or "--report" in args:
        if all_items:
            generate_report(all_items)
        elif not args or "--all" in args:
            print("\n（无爬取数据，跳过报告）")


if __name__ == "__main__":
    main()

"""
火箭板块爬虫 — 火箭发射日历、SpaceX、Blue Origin、Rocket Lab、Relativity Space、Stoke Space
"""

import re

from bs4 import BeautifulSoup

from .utils import fetch_html, fetch_json, parse_date


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


def crawl_blue_origin():
    """Blue Origin 官网新闻 → 日期+标题+摘要"""
    print("\n[Blue Origin] 抓取官网新闻...")
    try:
        html = fetch_html("https://www.blueorigin.com/news")
        soup = BeautifulSoup(html, "lxml")
        items = []

        skip_words = {"The Latest from Blue", "Space Systems", "Company",
                      "Press Inquiries", "Follow Blue Origin", "Subscribe",
                      "News", "Careers", "Sustainability"}

        for tag in ["h2", "h3", "h4"]:
            for h in soup.find_all(tag):
                title = h.get_text(strip=True)
                if not title or len(title) < 15 or title in skip_words:
                    continue
                if any(sw in title for sw in ["Blue Origin", "Subscribe", "Follow"]):
                    if len(title) < 30:
                        continue

                date_str = ""
                parent = h.find_parent()
                if parent:
                    text = parent.get_text(separator=" ")
                    date_match = re.search(
                        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})',
                        text)
                    if date_match:
                        date_str = parse_date(date_match.group(1))

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

        if len(items) < 3:
            all_text = soup.get_text(separator="\n")
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


def crawl_rocket_lab():
    """Rocket Lab 官网新闻 → 解析日期+标题"""
    print("\n[Rocket Lab] 抓取官网新闻...")
    try:
        html = fetch_html("https://www.rocketlabusa.com/updates/")
        soup = BeautifulSoup(html, "lxml")
        items = []

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


def crawl_spacex():
    """SpaceX 没有可抓的 HTML 新闻页（JS渲染），从 Launch Library API 提取"""
    print("\n[SpaceX] 通过 Launch Library API 提取最新发射...")
    try:
        data = fetch_json("https://ll.thespacedevs.com/2.2.0/launch/upcoming/",
                          params={"limit": 20, "ordering": "-net",
                                  "launch_service_provider": "SpaceX"})
        launches = data.get("results", [])
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


def crawl_relativity():
    """Relativity Space 官网新闻 — Terran R 可回收火箭"""
    print("\n[Relativity Space] 抓取官网新闻...")
    try:
        html = fetch_html("https://www.relativityspace.com/news")
        soup = BeautifulSoup(html, "lxml")
        items = []

        # Squarespace blog summary block — 尝试多种选择器
        for article in soup.select("article, .summary-item, .blog-item, [class*='blog-list'] a[href*='press-release']"):
            text = article.get_text(separator=" ", strip=True)
            if len(text) < 20:
                continue

            date_match = re.search(
                r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})',
                text)
            if not date_match:
                continue

            date_str = parse_date(date_match.group(1))
            after = text[date_match.end():].strip()
            title = after.split("Read")[0].strip()[:150]

            link = article.find("a") if article.name != "a" else article
            url = link.get("href", "") if link else ""

            if title and not any(i["title"] == title for i in items):
                items.append({
                    "source": "relativity",
                    "board": "rocket",
                    "title": title,
                    "date": date_str,
                    "summary": "",
                    "url": url or "https://www.relativityspace.com/news",
                })

        # 备用：全文正则
        if len(items) < 2:
            all_text = soup.get_text(separator="\n")
            pattern = re.compile(
                r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\s*\n\s*(.+?)(?:\n|$)',
                re.MULTILINE)
            for m in pattern.finditer(all_text):
                date_str = parse_date(m.group(1))
                title = m.group(2).strip()[:150]
                if title and len(title) > 10 and not any(i["title"] == title for i in items):
                    items.append({
                        "source": "relativity",
                        "board": "rocket",
                        "title": title,
                        "date": date_str,
                        "summary": "",
                        "url": "https://www.relativityspace.com/news",
                    })

        print(f"  解析到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"    {item['date'] or '?':<12} | {item['title'][:60]}")
        return items
    except Exception as e:
        print(f"  [Relativity Space] 失败: {e}")
        return []


def crawl_stoke():
    """Stoke Space 官网新闻 — Nova 全可回收火箭"""
    print("\n[Stoke Space] 抓取官网新闻...")
    try:
        html = fetch_html("https://www.stokespace.com/news/")
        soup = BeautifulSoup(html, "lxml")
        items = []

        for article in soup.find_all("article"):
            text = article.get_text(separator=" ", strip=True)
            if len(text) < 30:
                continue

            date_match = re.search(
                r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})',
                text)
            if not date_match:
                continue

            date_str = parse_date(date_match.group(1))
            title_tag = article.find(["h2", "h3"])
            title = title_tag.get_text(strip=True) if title_tag else ""
            if not title:
                continue

            link = article.find("a")
            url = link.get("href", "") if link else ""

            if title and not any(i["title"] == title for i in items):
                items.append({
                    "source": "stoke_space",
                    "board": "rocket",
                    "title": title,
                    "date": date_str,
                    "summary": "",
                    "url": url or "https://www.stokespace.com/news/",
                })

        print(f"  解析到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"    {item['date'] or '?':<12} | {item['title'][:60]}")
        return items
    except Exception as e:
        print(f"  [Stoke Space] 失败: {e}")
        return []

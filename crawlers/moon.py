"""
登月板块爬虫 — NASA Artemis
"""

import re

from bs4 import BeautifulSoup

from .utils import fetch_html


def crawl_nasa_artemis():
    """NASA Artemis → 尝试 RSS"""
    print("\n[NASA] 抓取 Artemis 新闻...")
    try:
        html = fetch_html("https://www.nasa.gov/missions/artemis/")
        soup = BeautifulSoup(html, "lxml")
        items = []

        for article in soup.find_all(["article", "div"], class_=lambda c: c and any(
            w in str(c).lower() for w in ["card", "article", "post", "news", "mission"]
        )):
            title_elem = article.find(["h2", "h3", "h4"])
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 10:
                continue

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

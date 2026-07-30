"""
核聚变板块爬虫 — ITER、CFS、ASIPP（中科院等离子体所）
"""

import re

from bs4 import BeautifulSoup

from .utils import fetch_html, parse_date


def crawl_iter():
    """ITER Newsline → 解析文章标题"""
    print("\n[ITER] 抓取 Newsline...")
    try:
        html = fetch_html("https://www.iter.org/newsline")
        if html is None:
            return []
        soup = BeautifulSoup(html, "lxml")
        items = []

        skip_words = {"Newsline archive", "Subscribe to the newsletter", "2026", "2025", "2024",
                      "Home", "News & Media", "Newsroom"}

        for tag in ["h2", "h3", "h4"]:
            for h in soup.find_all(tag):
                title = h.get_text(strip=True)
                if not title or len(title) < 10 or title in skip_words:
                    continue
                if any(sw in title for sw in skip_words):
                    continue

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
                        "board": "controlled-fusion",
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


def crawl_cfs():
    """CFS 官网新闻 → 解析标题"""
    print("\n[CFS] 抓取官网新闻...")
    try:
        html = fetch_html("https://cfs.energy/news-and-media")
        if html is None:
            return []
        soup = BeautifulSoup(html, "lxml")
        items = []

        skip_words = {"CFS in the News", "Join the power movement", "Press",
                      "Commonwealth Fusion Systems"}

        for tag in ["h2", "h3", "h4", "h5"]:
            for h in soup.find_all(tag):
                title = h.get_text(strip=True)
                if not title or len(title) < 15 or title in skip_words:
                    continue

                link = h.find("a")
                url = link.get("href", "") if link else ""
                if url and not url.startswith("http"):
                    url = "https://cfs.energy" + url

                if not any(i["title"] == title for i in items):
                    items.append({
                        "source": "cfs",
                        "board": "controlled-fusion",
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


def crawl_asipp():
    """ASIPP 新闻 → 解析中文新闻标题"""
    print("\n[ASIPP] 抓取中科院等离子体所...")
    try:
        html = fetch_html("http://www.ipp.cas.cn/xwdt/")
        if html is None:
            return []
        soup = BeautifulSoup(html, "lxml")
        items = []

        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            if not title or len(title) < 8:
                continue
            if any(w in title for w in ["首页", "登录", "注册", "搜索", "更多", "English", "设为首页"]):
                continue

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
                    "board": "controlled-fusion",
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

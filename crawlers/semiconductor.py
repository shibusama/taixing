"""
半导体板块爬虫 — 中芯国际 (SMIC)、上海微电子 (SMEE)
"""

import re

from bs4 import BeautifulSoup

from .utils import fetch_html, fetch_html_cffi, HAS_CFFI, parse_date


def crawl_smic():
    """中芯国际官网新闻 — 用 curl_cffi 绕过 Apache 403"""
    print("\n[SMIC] 抓取中芯国际新闻...")
    try:
        if HAS_CFFI:
            html = fetch_html_cffi("https://www.smics.com/site/news", timeout=30)
        else:
            print("  [SMIC] 需要 curl_cffi，回退到普通 requests（可能403）")
            html = fetch_html("https://www.smics.com/site/news", timeout=30)

        soup = BeautifulSoup(html, "lxml")
        items = []
        seen = set()

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

            parent = a.find_parent()
            date_str = ""
            summary = ""
            if parent:
                parent_text = parent.get_text(separator=" ", strip=True)
                date_match = re.search(r'(\d{4}-\d{1,2}-\d{1,2})', parent_text)
                if date_match:
                    date_str = date_match.group(1)
                after_title = parent_text.split(title, 1)
                if len(after_title) > 1:
                    summary = after_title[1].strip()[:200]
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

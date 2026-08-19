"""
超级工程板块爬虫 — 国铁集团
"""

import re

from bs4 import BeautifulSoup

from .utils import fetch_html, parse_date


def crawl_china_railway():
    """国铁集团官网新闻"""
    print("\n[国铁] 抓取国铁集团新闻...")
    try:
        html = fetch_html("https://www.china-railway.com.cn/")
        if html is None:
            return []
        soup = BeautifulSoup(html, "lxml")
        items = []
        seen_titles = set()

        for a in soup.find_all("a", href=True):
            title = a.get_text(strip=True)
            if not title or len(title) < 8:
                continue
            if any(w in title for w in ["首页", "登录", "English", "更多", "搜索", "网站地图"]):
                continue
            if title in seen_titles:
                continue
            seen_titles.add(title)

            parent = a.find_parent()
            date_str = ""
            if parent:
                date_match = re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', parent.get_text())
                if date_match:
                    date_str = parse_date(date_match.group(0).replace("年", "-").replace("月", "-").replace("/", "-"))

            href = a["href"]
            if href and not href.startswith("http"):
                href = "https://www.china-railway.com.cn" + href

            items.append({
                "source": "china_railway",
                "board": "mega-projects",
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

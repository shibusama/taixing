"""
中国科技板块爬虫 — Anthropic、DeepSeek、Moonshot（月之暗面）、OpenAI
"""

import re

from bs4 import BeautifulSoup

from .utils import fetch_html, fetch_html_cffi, HAS_CFFI, parse_date


def crawl_anthropic():
    """Anthropic Newsroom → 解析标题+日期+分类"""
    print("\n[Anthropic] 抓取 Newsroom...")
    try:
        html = fetch_html("https://www.anthropic.com/news")
        if html is None:
            return []
        soup = BeautifulSoup(html, "lxml")
        items = []
        seen_titles = set()

        for article in soup.find_all(["article", "div"], class_=lambda c: c and any(
            w in str(c).lower() for w in ["news", "post", "card", "article", "item"]
        )):
            text = article.get_text(separator=" ", strip=True)
            if len(text) < 20:
                continue

            date_match = re.search(r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})', text)
            date_str = parse_date(date_match.group(1)) if date_match else ""

            title = ""
            for tag in ["h2", "h3", "h4"]:
                h = article.find(tag)
                if h:
                    title = h.get_text(strip=True)
                    break

            if not title and date_match:
                before_date = text[:date_match.start()].strip()
                after_date = text[date_match.end():].strip()
                title = after_date.split(".")[0][:150] if after_date else before_date[:150]

            if title and title not in seen_titles:
                words = title.split()
                if len(words) > 12 and not title[0].isupper():
                    continue
                if re.match(r'^[A-Z][a-z]+ \d+ is a ', title):
                    continue
                seen_titles.add(title)
                items.append({
                    "source": "anthropic",
                    "board": "china-tech",
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
            except Exception:
                continue

        if not html:
            print("  [DeepSeek] 无法访问新闻页")
            return []

        soup = BeautifulSoup(html, "lxml")
        items = []
        seen_titles = set()

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

            href = a["href"]
            if href and not href.startswith("http"):
                href = "https://api-docs.deepseek.com" + href

            if title not in seen_titles:
                seen_titles.add(title)
                items.append({
                    "source": "deepseek",
                    "board": "china-tech",
                    "title": title,
                    "date": "",
                    "summary": "",
                    "url": href,
                })

        if len(items) < 3:
            try:
                html2 = fetch_html("https://www.deepseek.com/")
                if html2 is None:
                    html2 = ""
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
                    if title not in seen_titles:
                        seen_titles.add(title)
                        items.append({
                            "source": "deepseek",
                            "board": "china-tech",
                            "title": title,
                            "date": "",
                            "summary": "",
                            "url": href,
                        })
            except Exception:
                pass

        print(f"  解析到 {len(items)} 条新闻")
        for item in items[:5]:
            print(f"    {item['title'][:60]}")
        return items
    except Exception as e:
        print(f"  [DeepSeek] 失败: {e}")
        return []


def crawl_moonshot():
    """月之暗面官网 → 解析产品动态"""
    print("\n[Moonshot] 抓取官网动态...")
    try:
        html = fetch_html("https://www.moonshot.cn/")
        if html is None:
            return []
        soup = BeautifulSoup(html, "lxml")
        items = []

        raw_text = soup.get_text()
        date_matches = list(re.finditer(r'\d{4}-\d{2}-\d{2}', raw_text))
        seen_titles = set()
        for i, d in enumerate(date_matches):
            date_str = d.group(0)
            start = d.end()
            end = date_matches[i + 1].start() if i + 1 < len(date_matches) else min(start + 80, len(raw_text))
            title = raw_text[start:end].strip()
            title = re.split(r'[\u4e00-\u9fff]', title)[0].strip()
            if len(title) < 2 or len(title) > 50:
                continue
            if title not in seen_titles:
                seen_titles.add(title)
                items.append({
                    "source": "moonshot",
                    "board": "china-tech",
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


def crawl_openai():
    """OpenAI Blog → 解析文章标题（用 curl_cffi 绕过 Cloudflare）"""
    print("\n[OpenAI] 抓取 Blog...")
    try:
        if HAS_CFFI:
            html = fetch_html_cffi("https://openai.com/blog/", timeout=30)
        else:
            html = fetch_html("https://openai.com/blog/", timeout=20)
        if html is None:
            return []
        soup = BeautifulSoup(html, "lxml")
        items = []
        seen_titles = set()

        for article in soup.find_all(["article", "div"], class_=lambda c: c and any(
            w in str(c).lower() for w in ["post", "article", "card", "blog"]
        )):
            title_elem = article.find(["h2", "h3", "h4"])
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            if title in seen_titles:
                continue
            seen_titles.add(title)

            date_str = ""
            time_elem = article.find("time")
            if time_elem:
                date_str = time_elem.get("datetime", "")[:10]

            link = title_elem.find("a")
            url = link.get("href", "") if link else ""
            if url and not url.startswith("http"):
                url = "https://openai.com" + url

            items.append({
                "source": "openai",
                "board": "china-tech",
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

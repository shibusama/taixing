"""
Generic RSS/Atom crawler - config-driven, one module for all boards.
Sources with "type": "rss" in data_sources.json are auto-registered by
crawler_registry as crawl_rss_<source_id> crawlers (feed_url/category
come from the config, no per-site scripts needed).
"""
import hashlib
import re
import sys
from datetime import datetime
from email.utils import parsedate_to_datetime

# avoid UnicodeEncodeError on GBK consoles when printing exotic chars
try:
    sys.stdout.reconfigure(errors="replace")
except Exception:
    pass

import requests
import feedparser

from .http_utils import HEADERS


def _strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())[:500]


def _entry_image(entry):
    for key in ("media_content", "media_thumbnail"):
        vals = entry.get(key) or []
        for v in vals:
            if isinstance(v, dict) and v.get("url"):
                return v["url"]
    # thumbnail from content html
    raw = ""
    content = entry.get("content") or []
    if content:
        raw = content[0].get("value", "")
    if not raw:
        raw = entry.get("summary", "")
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw)
    return m.group(1) if m else ""


def _entry_publish_time(entry):
    pub = entry.get("published") or entry.get("updated") or ""
    if not pub:
        return ""
    try:
        return parsedate_to_datetime(pub).isoformat()
    except Exception:
        return pub


def _entry_to_item(entry, source_name, category, language):
    url = (entry.get("link") or "").strip()
    title = (entry.get("title") or "").strip()
    if not url or not title:
        return None
    summary = _strip_html(entry.get("summary") or "")
    if not summary and entry.get("content"):
        summary = _strip_html(entry["content"][0].get("value", ""))
    news_id = hashlib.sha256(url.encode()).hexdigest()[:16]
    return {
        "news_id": news_id,
        "source_name": source_name,
        "source_url": url,
        "crawl_time": datetime.utcnow().isoformat() + "Z",
        "publish_time": _entry_publish_time(entry),
        "title": title[:200],
        "raw_content": summary,
        "summary": "",
        "cover_image": _entry_image(entry),
        "images": "[]",
        "tags": "[]",
        "category": category,
        "hot_score": 0,
        "sentiment": "neutral",
        "language": language,
        "status": "pending",
    }


_RSS_HEADERS = {
    "User-Agent": HEADERS.get("User-Agent", "Mozilla/5.0"),
    "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
}


def _fetch_feed(feed_url, timeout=20):
    resp = requests.get(feed_url, headers=_RSS_HEADERS, timeout=timeout, verify=False)
    resp.raise_for_status()
    return feedparser.parse(resp.content)


def make_rss_crawler(feed_url, source_name, category, board_id, language="en", limit=20):
    """Build a zero-arg crawler callable for one RSS source."""
    def crawl():
        print(f"\n[RSS] {source_name} -> {feed_url}")
        try:
            feed = _fetch_feed(feed_url)
            if feed.bozo and not feed.entries:
                print(f"  [RSS] parse failed: {feed.bozo_exception}")
                return []
            items = []
            for entry in feed.entries[:limit]:
                item = _entry_to_item(entry, source_name, category, language)
                if item:
                    items.append(item)
            print(f"  [RSS] got {len(items)} items")
            for item in items[:8]:
                print(f"    {(item['publish_time'] or '?')[:10]} | {item['title'][:55]}")
            return items
        except Exception as e:
            print(f"  [RSS] failed: {e}")
            return []
    return crawl

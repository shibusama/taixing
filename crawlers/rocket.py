"""
火箭板块爬虫 — 火箭发射日历 + SNAPI 航天新闻聚合
数据源：
  - Launch Library 2 API：发射日历（结构化数据）
  - Spaceflight News API (SNAPI)：航天新闻聚合（35000+ 篇，20+ 权威来源）
"""

import requests

from .utils import fetch_json


# SNAPI 搜索关键词 → 公司映射
ROCKET_COMPANIES = {
    "SpaceX": "spacex",
    "Blue Origin": "blue_origin",
    "Rocket Lab": "rocket_lab",
    "Relativity Space": "relativity",
    "Stoke Space": "stoke_space",
}

# API 请求头（Accept: application/json 确保返回 JSON）
API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def fetch_json_api(url, params=None, timeout=15):
    """专为 JSON API 设计的请求函数，确保返回 JSON"""
    resp = requests.get(url, params=params, timeout=timeout, headers=API_HEADERS, verify=False)
    resp.raise_for_status()
    return resp.json()


def crawl_rocket_launches():
    """火箭发射日历 → 结构化数据（Launch Library 2 API）"""
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


def crawl_rocket_news_snapi():
    """
    通过 Spaceflight News API (SNAPI) 获取可回收火箭公司新闻
    聚合来源：NASASpaceflight, SpaceNews, NASA, Ars Technica, Spaceflight Now 等 20+ 权威媒体
    """
    print("\n[SNAPI] 抓取可回收火箭公司新闻...")
    all_items = []

    for company, source_id in ROCKET_COMPANIES.items():
        try:
            # SNAPI v4: 搜索关键词，按时间倒序，取最新 20 条
            data = fetch_json_api(
                "https://api.spaceflightnewsapi.net/v4/articles/",
                params={"search": company, "limit": 20, "ordering": "-published_at"}
            )
            articles = data.get("results", [])
            count = data.get("count", 0)
            print(f"  [{company}] 共 {count} 篇，获取最新 {len(articles)} 篇")

            for article in articles:
                # 解析日期：SNAPI 返回 ISO 格式 "2026-07-29T01:24:07Z"
                pub_date = article.get("published_at", "")
                if pub_date:
                    pub_date = pub_date[:10]  # 取 "2026-07-29"

                # 提取摘要（去除 HTML 标签和多余空白）
                summary = article.get("summary", "")
                if summary:
                    # 去除可能的换行和多余空格
                    summary = " ".join(summary.split())[:300]

                # 提取新闻来源
                news_site = article.get("news_site", "")

                # 提取作者
                authors = article.get("authors", [])
                author_str = ", ".join(a.get("name", "") for a in authors[:3]) if authors else ""

                all_items.append({
                    "source": source_id,
                    "board": "rocket",
                    "title": article.get("title", ""),
                    "date": pub_date,
                    "summary": summary,
                    "url": article.get("url", ""),
                    "image_url": article.get("image_url", ""),
                    "news_site": news_site,
                    "author": author_str,
                    "company": company,
                })

        except Exception as e:
            print(f"  [{company}] SNAPI 查询失败: {e}")

    print(f"\n  [SNAPI] 共获取 {len(all_items)} 条新闻")
    for item in all_items[:10]:
        print(f"    {item['date'] or '?':<12} | {item['company']:<16} | {item['title'][:50]}")

    return all_items

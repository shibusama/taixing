"""
火箭板块爬虫 — 火箭发射日历 + SNAPI 航天新闻聚合
数据源：
  - Launch Library 2 API：发射日历（结构化数据）
  - Spaceflight News API (SNAPI)：航天新闻聚合（35000+ 篇，20+ 权威来源）
"""

import hashlib
import requests
from datetime import datetime

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


def fetch_json_api(url, params=None, timeout=15, retries=3):
    """专为 JSON API 设计的请求函数，确保返回 JSON，支持重试"""
    import time
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout, headers=API_HEADERS, verify=False)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and attempt < retries - 1:
                wait_time = (attempt + 1) * 10  # 10s, 20s, 30s
                print(f"    限流，等待 {wait_time}s 后重试...")
                time.sleep(wait_time)
            else:
                raise


def generate_news_id(url):
    """根据 URL 生成唯一哈希 ID"""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def crawl_rocket_launches():
    """火箭发射日历 → rocket_launch_timeline 表（Launch Library 2 API）"""
    print("\n[火箭发射] 抓取 Launch Library 2 API...")
    try:
        data = fetch_json_api("https://ll.thespacedevs.com/2.2.0/launch/upcoming/",
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
            
            launch_url = l.get("url", "")
            timeline_id = generate_news_id(launch_url) if launch_url else generate_news_id(l.get("name", ""))
            
            # 判断发射结果
            status_name = l.get("status", {}).get("name", "") if l.get("status") else ""
            if "Go" in status_name or "TBC" in status_name:
                outcome = "计划中"
            elif "Success" in status_name:
                outcome = "成功"
            elif "Partial" in status_name:
                outcome = "部分成功"
            elif "Failure" in status_name:
                outcome = "失败"
            else:
                outcome = status_name or "计划中"
            
            # 构建简短描述
            rocket_name = l.get("rocket", {}).get("configuration", {}).get("name", "")
            mission_name = l.get("mission", {}).get("name", "") if l.get("mission") else ""
            brief_desc = f"{agency} {rocket_name} 执行 {mission_name}" if mission_name else f"{agency} {rocket_name}"
            
            items.append({
                "timeline_id": timeline_id,
                "rocket_id": None,  # 后续关联 rocket_companies 表
                "mission_name": l.get("name", ""),
                "launch_time": l.get("net", "")[:10],
                "launch_site": l.get("pad", {}).get("location", {}).get("name", "") if l.get("pad") else "",
                "payload": mission_name,
                "outcome": outcome,
                "reuse_status": "",  # LL2 API 不直接提供回收状态
                "brief_desc": brief_desc,
                "related_news_ids": [],
                "create_time": datetime.now().isoformat(),
                "update_time": datetime.now().isoformat(),
            })

        print(f"  获取 {len(items)} 条关注火箭发射")
        for item in items[:8]:
            print(f"    {item['launch_time']} | {item['outcome']:<6} | {item['mission_name'][:50]}")
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
    返回符合新 raw_articles 表结构的数据
    """
    print("\n[SNAPI] 抓取可回收火箭公司新闻...")
    all_items = []
    crawl_time = datetime.utcnow().isoformat() + "Z"

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
                source_url = article.get("url", "")
                if not source_url:
                    continue

                # 生成唯一 news_id
                news_id = generate_news_id(source_url)

                # 解析发布时间
                publish_time = article.get("published_at", "")

                # 提取摘要
                summary = article.get("summary", "")
                if summary:
                    summary = " ".join(summary.split())[:500]

                # 提取新闻来源
                news_site = article.get("news_site", "")

                # 提取作者
                authors = article.get("authors", [])
                author_str = ", ".join(a.get("name", "") for a in authors[:3]) if authors else ""

                # 封面图片
                cover_image = article.get("image_url", "")

                # 构建符合新表结构的数据
                all_items.append({
                    "news_id": news_id,
                    "source_name": news_site,
                    "source_url": source_url,
                    "crawl_time": crawl_time,
                    "publish_time": publish_time if publish_time else None,
                    "title": article.get("title", ""),
                    "raw_content": summary,  # SNAPI 只提供摘要，无正文
                    "summary": "",  # AI 摘要待生成
                    "cover_image": cover_image,
                    "images": "[]",  # JSON 数组
                    "tags": f'["航天", "{company}"]',  # JSON 数组
                    "category": "航空航天",
                    "hot_score": 0,  # 待 AI 评分
                    "sentiment": "neutral",
                    "event_group_id": None,
                    "language": "en",
                    "status": "pending",
                    # 额外字段（不入库，用于日志）
                    "_company": company,
                    "_author": author_str,
                })

            # 避免触发 SNAPI 速率限制
            import time
            time.sleep(1)

        except Exception as e:
            print(f"  [{company}] SNAPI 查询失败: {e}")

    print(f"\n  [SNAPI] 共获取 {len(all_items)} 条新闻")
    for item in all_items[:5]:
        pub_time = item.get('publish_time') or ''
        print(f"    {pub_time[:10] if pub_time else '?':<12} | {item['_company']:<16} | [{item['source_name']}] {item['title'][:50]}")

    return all_items

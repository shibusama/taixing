"""
火箭板块爬虫 — 火箭发射日历 + SNAPI 航天新闻聚合
数据源：
  - Launch Library 2 API：发射日历（结构化数据）
  - Spaceflight News API (SNAPI)：航天新闻聚合（35000+ 篇，20+ 权威来源）
"""

import hashlib
import re
from datetime import datetime

from bs4 import BeautifulSoup

from .utils import fetch_json, fetch_html, fetch_ai_fallback


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

# LL2 返回的机构名 → 中文（仅翻译中国企业；SpaceX/Blue Origin/Rocket Lab 等国外公司
# 按中文媒体惯例保留英文原名，不在此列表中）
AGENCY_ZH_MAP = [
    ("china aerospace science and technology", "航天科技集团"),
    ("casc", "航天科技集团"),
    ("landspace", "蓝箭航天"),
    ("galactic energy", "星河动力"),
    ("space pioneer", "天兵科技"),
    ("ispace", "星际荣耀"),
    ("expace", "航天科工"),
]

# 火箭型号名 → 中文（覆盖 WATCH 名单里常见型号；未收录的新名词保留英文原文）
ROCKET_NAME_ZH_MAP = [
    ("falcon heavy", "猎鹰重型"),
    ("falcon 9", "猎鹰9号"),
    ("starship", "星舰"),
    ("new glenn", "新格伦"),
    ("electron", "电子号"),
    ("long march 2", "长征二号"),
    ("long march 3", "长征三号"),
    ("long march 4", "长征四号"),
    ("long march 5", "长征五号"),
    ("long march 6", "长征六号"),
    ("long march 7", "长征七号"),
    ("long march 8", "长征八号"),
    ("long march 10", "长征十号"),
    ("long march 11", "长征十一号"),
    ("long march 12", "长征十二号"),
    ("zhuque-2", "朱雀二号"),
    ("zhuque-3", "朱雀三号"),
    ("ceres-1", "谷神星一号"),
    ("ceres 1", "谷神星一号"),
    ("pallas-1", "智神星一号"),
    ("pallas 1", "智神星一号"),
    ("tianlong-2", "天龙二号"),
    ("tianlong-3", "天龙三号"),
    ("hyperbola-1", "双曲线一号"),
    ("hyperbola-3", "双曲线三号"),
    ("kuaizhou", "快舟"),
    ("kinetica", "引力"),
]

# 发射场名 → 中文（未收录的保留英文原文）
LAUNCH_SITE_ZH_MAP = [
    ("vandenberg", "美国范登堡基地"),
    ("cape canaveral", "美国卡纳维拉尔角"),
    ("kennedy space center", "美国肯尼迪航天中心"),
    ("starbase", "美国星舰基地（博卡奇卡）"),
    ("jiuquan", "中国酒泉卫星发射中心"),
    ("xichang", "中国西昌卫星发射中心"),
    ("taiyuan", "中国太原卫星发射中心"),
    ("wenchang", "中国文昌航天发射场"),
    ("hainan", "中国海南商业航天发射场"),
    ("guiana space centre", "法属圭亚那航天中心"),
    ("baikonur", "拜科努尔发射场"),
]


def _zh_lookup(name, mapping):
    """按子串匹配翻译；找不到就原样返回英文（保留原文兜底）"""
    if not name:
        return name
    low = name.lower()
    for key, zh in mapping:
        if key in low:
            return zh
    return name


def zh_agency_name(name):
    return _zh_lookup(name, AGENCY_ZH_MAP)


def zh_rocket_name(name):
    return _zh_lookup(name, ROCKET_NAME_ZH_MAP)


def zh_launch_site(name):
    return _zh_lookup(name, LAUNCH_SITE_ZH_MAP)


def generate_news_id(url):
    """根据 URL 生成唯一哈希 ID"""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def crawl_rocket_launches():
    """火箭发射日历（Launch Library 2 API）"""
    print("\n[火箭发射] 抓取 Launch Library 2 API...")
    try:
        data = fetch_json("https://ll.thespacedevs.com/2.2.0/launch/upcoming/",
                          params={"limit": 50, "ordering": "net"}, headers=API_HEADERS)
        if data is None:
            print("  LL2 API 被限流，跳过")
            return []
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
            
            # 构建简短描述（机构/火箭型号翻成中文，任务/卫星专有名词保留英文原文）
            rocket_name = l.get("rocket", {}).get("configuration", {}).get("name", "")
            mission_name = l.get("mission", {}).get("name", "") if l.get("mission") else ""
            zh_agency = zh_agency_name(agency)
            zh_rocket = zh_rocket_name(rocket_name)
            zh_site = zh_launch_site(l.get("pad", {}).get("location", {}).get("name", "") if l.get("pad") else "")
            title_zh = f"{zh_agency} {zh_rocket}" + (f" · {mission_name}" if mission_name else "")
            brief_desc = f"{zh_agency} {zh_rocket} 执行 {mission_name}" if mission_name else f"{zh_agency} {zh_rocket}"

            items.append({
                "timeline_id": timeline_id,
                "rocket_id": None,
                "mission_name": title_zh,
                "launch_time": l.get("net", "")[:10],
                "launch_site": zh_site,
                "payload": mission_name,
                "outcome": outcome,
                "reuse_status": "",
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
        print("  [AI兜底] 尝试用 DeepSeek 补充数据...")
        return fetch_ai_fallback("可回收火箭和商业航天发射", count=15)


def crawl_spacechina_launches():
    """长征系列运载火箭发射记录（航天科技集团官网，纯中文官方数据，不依赖 LL2，无限流风险）

    只有已发射成功的历史记录，没有未来发射计划，用于补充"发射计划"Tab"已完成"一侧；
    与 crawl_rocket_launches（LL2）覆盖同一批国家队发射时可能产生重复条目（各自的
    timeline_id 生成方式不同，暂不做跨数据源去重）。
    """
    print("\n[长征发射记录] 抓取航天科技集团官网...")
    url = "https://www.spacechina.com/n25/n142/n152/n657792/c3556658/content.html"
    try:
        html = fetch_html(url)
        if html is None:
            return []
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table", class_="MsoNormalTable")
        if table is None:
            print("  未找到发射记录表格，页面结构可能已变化")
            return []

        rows = table.find_all("tr")[1:]  # 跳过表头
        items = []
        for tr in rows[:40]:  # 只取最近 40 条，避免时间线过长
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cells) < 5:
                continue
            seq, rocket_name, date_raw, payload, site = cells[:5]
            if not rocket_name or not date_raw:
                continue

            date_norm = date_raw.replace(".", "-").strip()
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_norm):
                continue

            timeline_id = generate_news_id(f"spacechina-{seq}")
            title = f"航天科技集团 {rocket_name}" + (f" · {payload}" if payload else "")
            brief_desc = f"航天科技集团 {rocket_name} 成功发射 {payload}" if payload else f"航天科技集团 {rocket_name} 成功发射"

            items.append({
                "timeline_id": timeline_id,
                "rocket_id": None,
                "mission_name": title,
                "launch_time": date_norm,
                "launch_site": site,
                "payload": payload,
                "outcome": "成功",
                "reuse_status": "",
                "brief_desc": brief_desc,
                "related_news_ids": [],
                "create_time": datetime.now().isoformat(),
                "update_time": datetime.now().isoformat(),
            })

        print(f"  获取 {len(items)} 条长征系列发射记录")
        for item in items[:8]:
            print(f"    {item['launch_time']} | {item['mission_name'][:50]}")
        return items
    except Exception as e:
        print(f"  [长征发射记录] 抓取失败: {e}")
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
            data = fetch_json(
                "https://api.spaceflightnewsapi.net/v4/articles/",
                params={"search": company, "limit": 20, "ordering": "-published_at"},
                headers=API_HEADERS,
            )
            if data is None:
                print(f"  [{company}] SNAPI 被限流，跳过")
                continue
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
                    "category": "rocket",
                    "hot_score": 0,  # 待 AI 评分
                    "sentiment": "neutral",
                    "event_group_id": None,
                    "language": "en",
                    "status": "pending",
                    # 额外字段（不入库，用于日志）
                    "_company": company,
                    "_author": author_str,
                })

        except Exception as e:
            print(f"  [{company}] SNAPI 查询失败: {e}")

    print(f"\n  [SNAPI] 共获取 {len(all_items)} 条新闻")
    if not all_items:
        print("  [AI兜底] SNAPI 无数据，尝试用 DeepSeek 补充...")
        return fetch_ai_fallback("可回收火箭和商业航天", count=20)
    for item in all_items[:5]:
        pub_time = item.get('publish_time') or ''
        print(f"    {pub_time[:10] if pub_time else '?':<12} | {item['_company']:<16} | [{item['source_name']}] {item['title'][:50]}")

    return all_items

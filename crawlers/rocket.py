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
    # 中国民营火箭公司（SNAPI 英文源，文章量少但能覆盖国际报道）
    "LandSpace": "landspace",
    "Galactic Energy": "galactic_energy",
    "iSpace": "ispace",
    "Orienspace": "orienspace",
    "CAS Space": "cas_space",
    "Deep Blue Aerospace": "deep_blue",
}

# API 请求头（Accept: application/json 确保返回 JSON）
API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

# 关注的公司/机构名单（LL2 与备用源共用）
WATCH_AGENCIES = [
    "SpaceX", "Blue Origin", "Rocket Lab", "CASC",
    "LandSpace", "Galactic Energy", "Space Pioneer", "iSpace",
    "ExPace", "Isar Aerospace", "Rocket Factory", "Firefly",
    "OrienSpace", "CAS Space", "Deep Blue", "Rocket Pi",
]

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
    ("orienspace", "东方空间"),
    ("orien space", "东方空间"),
    ("cas space", "中科宇航"),
    ("deep blue", "深蓝航天"),
    ("rocket pi", "箭元科技"),
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
    ("gravity-1", "引力一号"),
    ("gravity 1", "引力一号"),
    ("gravity-2", "引力二号"),
    ("gravity 2", "引力二号"),
    ("lijian", "力箭"),
    ("shuangquxian", "双曲线"),
    ("yuanxingzhe", "元行者"),
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


# LL2 任务名（mission.name）→ 中文（专有名词按中文媒体惯例翻译/保留，长条目在前优先匹配）
MISSION_ZH_MAP = [
    ("nancy grace roman space telescope", "罗曼空间望远镜任务"),
    ("griffin mission one", "格里芬一号月球任务"),
    ("the lightning god defends", "雷神守护任务（iQPS雷达卫星）"),
    ("onward and upward", "勇往直前首飞任务"),
    ("starlink group", "星链组网任务"),
    ("sda tranche 1 tracking layer", "SDA第1代追踪层卫星"),
    ("sda tranche 1 transport layer", "SDA第1代传输层卫星"),
    ("hawkeye 360", "HawkEye 360电子侦察卫星"),
    ("strix launch", "StriX雷达卫星发射"),
    ("blacksky gen-3", "BlackSky第三代卫星"),
    ("o3b mpower", "O3b mPower高通量卫星"),
    ("transporter", "拼车发射任务"),
    ("cygnus crs-2", "天鹅座货运飞船任务"),
    ("dragon crs-2", "龙货运飞船任务"),
    ("rivada", "Rivada通信卫星"),
    ("loxsat", "LOXSAT液氧推进演示卫星"),
    ("roman", "罗曼空间望远镜"),
    ("amazon kuiper", "柯伊伯星座"),
    ("demo flight", "演示飞行"),
]


def zh_mission_name(name):
    """任务名翻译：Flight N → 第N次试飞、Crew-N → 载人龙飞船N号；其余按映射表子串匹配，找不到保留英文"""
    if not name:
        return name
    m = re.match(r"^flight\s+(\d+)$", name, re.I)
    if m:
        return f"第{m.group(1)}次试飞"
    m = re.match(r"^crew[- ](\d+)$", name, re.I)
    if m:
        return f"载人龙飞船{m.group(1)}号"
    return _zh_lookup(name, MISSION_ZH_MAP)


def generate_news_id(url):
    """根据 URL 生成唯一哈希 ID"""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _nested_get(obj, *path, default=""):
    """从嵌套 dict 中安全取字段，避免 None/非 dict 时报错"""
    cur = obj
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
        if cur is None:
            return default
    return cur if cur is not None else default


def _build_launch_item(l):
    """把不同来源的单个发射对象统一成 rocket_launch_timeline 需要的结构。

    兼容 LL2 v2.2、LL2 v2.1（spacelaunchnow.me）以及部分公开 JSON API 的常见字段差异。
    """
    if not isinstance(l, dict):
        return None

    # 机构名兼容：launch_service_provider / provider / agency
    provider = l.get("launch_service_provider")
    if not isinstance(provider, dict):
        provider = l.get("provider")
    agency = provider.get("name", "") if isinstance(provider, dict) else (l.get("agency", "") or "")
    if not any(w.lower() in str(agency).lower() for w in WATCH_AGENCIES):
        return None

    # URL / 唯一键
    launch_url = l.get("url", "") or l.get("slug", "") or ""
    name = l.get("name", "") or l.get("mission_name", "") or ""
    timeline_id = generate_news_id(launch_url) if launch_url else generate_news_id(name)

    # 火箭名称兼容：rocket.configuration.name / vehicle.name / rocket_name
    rocket_obj = l.get("rocket")
    if not isinstance(rocket_obj, dict):
        rocket_obj = l.get("vehicle")
    rocket_name = ""
    if isinstance(rocket_obj, dict):
        rocket_name = _nested_get(rocket_obj, "configuration", "name") or rocket_obj.get("name", "")
    if not rocket_name:
        rocket_name = l.get("rocket_name", "")

    # 任务名兼容：mission.name / mission.description / mission_name
    mission_obj = l.get("mission")
    mission_name = ""
    if isinstance(mission_obj, dict):
        mission_name = mission_obj.get("name", "") or mission_obj.get("description", "")
    if not mission_name:
        mission_name = l.get("mission_name", "")

    # 发射场兼容：pad.location.name / pad.name / location
    pad_obj = l.get("pad")
    zh_site = ""
    if isinstance(pad_obj, dict):
        zh_site = zh_launch_site(_nested_get(pad_obj, "location", "name") or pad_obj.get("name", ""))
    else:
        zh_site = zh_launch_site(str(l.get("location", "")))

    # 发射时间兼容：net / window_start / start
    raw_time = l.get("net") or l.get("window_start") or l.get("start") or ""
    launch_time = str(raw_time)[:10] if raw_time else ""

    # 状态兼容：status.name（dict）或 status（字符串）
    status_obj = l.get("status")
    status_name = status_obj.get("name", "") if isinstance(status_obj, dict) else str(status_obj or "")
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

    zh_agency = zh_agency_name(str(agency))
    zh_rocket = zh_rocket_name(rocket_name)
    zh_mission = zh_mission_name(mission_name)
    title_zh = f"{zh_agency} {zh_rocket}" + (f" · {zh_mission}" if zh_mission else "")
    brief_desc = f"{zh_agency} {zh_rocket} 执行 {zh_mission}" if zh_mission else f"{zh_agency} {zh_rocket}"

    return {
        "timeline_id": timeline_id,
        "rocket_id": None,
        "mission_name": title_zh,
        "launch_time": launch_time,
        "launch_site": zh_site,
        "payload": zh_mission,
        "outcome": outcome,
        "reuse_status": "",
        "brief_desc": brief_desc,
        "related_news_ids": [],
        "create_time": datetime.now().isoformat(),
        "update_time": datetime.now().isoformat(),
    }


def _extract_launch_list(data):
    """兼容不同 API 返回结构：list / {results:[...]} / {result:[...]} / {launches:[...]} / {data:[...]}"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("results", "result", "launches", "data"):
            val = data.get(key)
            if isinstance(val, list):
                return val
    return []


def _crawl_rocket_launches_backup():
    """LL2 主源无数据/被限流时，尝试其他公开真实数据源。

    当前备用源：
      1. spacelaunchnow.me 提供的 Launch Library 2.1.0 API（同源镜像，测试可用）
      2. fdo.rocketlaunch.live 公开 JSON API（测试可用）
    若备用源也没有数据，则返回空列表（不编造数据）。
    """
    print("\n[火箭发射] LL2 主源无数据，尝试备用真实数据源...")
    backup_sources = [
        ("https://spacelaunchnow.me/api/ll/2.1.0/launch/upcoming/", {"limit": 50}),
        ("https://fdo.rocketlaunch.live/json/launches/upcoming/50", None),
    ]

    for url, params in backup_sources:
        try:
            data = fetch_json(url, params=params, headers=API_HEADERS, timeout=15)
            if data is None:
                print(f"  [备用源] {url} 无响应，跳过")
                continue
            launches = _extract_launch_list(data)
            print(f"  [备用源] {url} 返回原始发射 {len(launches)} 条")
            if not launches:
                continue

            items = []
            for l in launches:
                item = _build_launch_item(l)
                if item:
                    items.append(item)

            print(f"  [备用源] 过滤后获得 {len(items)} 条关注发射")
            if items:
                return items
        except Exception as e:
            print(f"  [备用源] {url} 抓取失败: {e}")
            continue

    print("  [备用源] 均未获取到关注发射，保持空数据")
    return []


def crawl_rocket_launches():
    """火箭发射日历（Launch Library 2 API + 备用真实数据源）"""
    print("\n[火箭发射] 抓取 Launch Library 2 API...")
    try:
        data = fetch_json("https://ll.thespacedevs.com/2.2.0/launch/upcoming/",
                          params={"limit": 50, "ordering": "net"}, headers=API_HEADERS)
        if data is None:
            print("  LL2 API 被限流/无响应，尝试备用源...")
            return _crawl_rocket_launches_backup()

        launches = data.get("results", [])
        items = []
        for l in launches:
            item = _build_launch_item(l)
            if item:
                items.append(item)

        print(f"  获取 {len(items)} 条关注火箭发射")
        for item in items[:8]:
            print(f"    {item['launch_time']} | {item['outcome']:<6} | {item['mission_name'][:50]}")

        if not items:
            print("  LL2 主源未匹配到关注发射，尝试备用源...")
            return _crawl_rocket_launches_backup()
        return items
    except Exception as e:
        print(f"  [火箭发射] API失败: {e}")
        print("  [火箭发射] 尝试备用真实数据源...")
        backup_items = _crawl_rocket_launches_backup()
        if backup_items:
            return backup_items
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


def crawl_landspace_news():
    """蓝箭航天官网新闻中心（国内民营官方源）

    抓取 news.html 的新闻列表（标题 + 日期 + 详情链接），入库 raw_articles（category=rocket）。
    官网无正文摘要，仅标题/日期/链接；发射计划不在官网公布，仍依赖 LL2。
    """
    print("\n[蓝箭新闻] 抓取蓝箭航天官网新闻中心...")
    url = "https://www.landspace.com/news.html"
    try:
        html = fetch_html(url)
        if html is None:
            return []
        soup = BeautifulSoup(html, "lxml")
        items = []
        seen = set()
        crawl_time = datetime.utcnow().isoformat() + "Z"

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "news-detail.html" not in href or "itemid=" not in href:
                continue
            title = a.get_text(strip=True)
            # 跳过 "Learn more" 等非新闻链接文本（同一链接的次要文本节点）
            if not title or len(title) < 5 or title.lower() in ("learn more", "查看更多", "了解更多"):
                continue
            if title in seen:
                continue
            seen.add(title)

            # 详情页 URL
            if href.startswith("http"):
                detail_url = href
            else:
                detail_url = "https://www.landspace.com/" + href.lstrip("/")

            # 从标题解析日期并去除日期前缀：
            # 支持 "2026-07-02标题" / "0906月2026标题" / "2026年9月6日标题"
            publish_time = ""
            m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", title)
            if m:
                publish_time = f"{m.group(1)}-{m.group(2)}-{m.group(3)}T00:00:00"
                title = re.sub(r"^\d{4}-\d{2}-\d{2}", "", title).strip()
            else:
                m2 = re.match(r"^(\d{2})(\d{2})月(\d{4})", title)
                if m2:
                    # "1405月2026" = 2026年5月14日（前两位日、后两位月）
                    day, month, year = m2.group(1), m2.group(2), m2.group(3)
                    if 1 <= int(month) <= 12:
                        publish_time = f"{year}-{month}-{day}T00:00:00"
                        title = re.sub(r"^\d{2}\d{2}月\d{4}", "", title).strip()
                else:
                    m3 = re.match(r"^(\d{4})年(\d{1,2})月(\d{1,2})日", title)
                    if m3:
                        publish_time = f"{m3.group(1)}-{m3.group(2).zfill(2)}-{m3.group(3).zfill(2)}T00:00:00"
                        title = re.sub(r"^\d{4}年\d{1,2}月\d{1,2}日", "", title).strip()

            items.append({
                "news_id": generate_news_id(detail_url),
                "source_name": "蓝箭航天",
                "source_url": detail_url,
                "crawl_time": crawl_time,
                "publish_time": publish_time,
                "title": title[:200],
                "raw_content": "",
                "summary": "",
                "cover_image": "",
                "images": "[]",
                "tags": '["民营航天", "蓝箭航天"]',
                "category": "rocket",
                "hot_score": 0,
                "sentiment": "neutral",
                "language": "zh",
                "status": "pending",
            })

        print(f"  获取 {len(items)} 条蓝箭新闻")
        for item in items[:8]:
            print(f"    {(item['publish_time'] or '?')[:10]:<12} | {item['title'][:50]}")
        return items
    except Exception as e:
        print(f"  [蓝箭新闻] 抓取失败: {e}")
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

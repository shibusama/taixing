"""
AI 新闻提取模块
从 raw_articles 中提取结构化数据，写入 rocket_launch_timeline
"""

import json
import hashlib
import requests
from datetime import datetime
from typing import List, Dict, Optional

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-v4-flash"
DEEPSEEK_API_KEY = "sk-REMOVED"


EXTRACTION_PROMPT = """你是航天新闻结构化提取专家。根据以下新闻内容，提取发射任务信息。

新闻标题：{title}
新闻摘要：{summary}
新闻正文：{raw_content}
来源媒体：{source_name}
发布时间：{publish_time}

请输出 JSON 格式（只输出 JSON，不要其他内容）：
{{
  "rocket_id": "火箭型号标识（如 falcon9、starship、newglenn、electron、terranr、nova 等，无法判断则为 null）",
  "mission_name": "任务名称（如 Starlink Group 12-3、Artemis II 等）",
  "launch_time": "发射时间（YYYY-MM-DD 或 YYYY-MM 或 YYYY，无法判断则为 null）",
  "launch_site": "发射场（如 卡纳维拉尔角、肯尼迪航天中心、酒泉、文昌 等）",
  "payload": "载荷描述（如 Starlink 卫星、载人飞船 等）",
  "outcome": "发射结果，只能是以下之一：成功、失败、部分成功、计划中、未知",
  "reuse_status": "一级回收状态，只能是以下之一：回收成功、回收失败、无回收、未知",
  "brief_desc": "一句话描述，50字以内，中文",
  "confidence": 0.0到1.0之间的数字，表示你对提取结果的把握程度
}}

注意：
1. 如果新闻不包含发射任务信息（如纯评论、政策分析），confidence 设为 0
2. 如果信息不完整，对应字段设为 null
3. brief_desc 用中文，简洁明了
4. 只输出 JSON，不要 markdown 代码块标记"""


def call_deepseek(prompt: str) -> Optional[Dict]:
    """调用 DeepSeek API"""
    try:
        resp = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 1000
            },
            timeout=30
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        # 清理可能的 markdown 标记
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return json.loads(content)
    except Exception as e:
        print(f"  [AI] API 调用失败: {e}")
        return None


def extract_timeline_from_article(article: Dict) -> Optional[Dict]:
    """从单条新闻中提取时间线数据"""
    prompt = EXTRACTION_PROMPT.format(
        title=article.get("title", ""),
        summary=article.get("summary", ""),
        raw_content=article.get("raw_content", "") or "",
        source_name=article.get("source_name", ""),
        publish_time=article.get("publish_time", "")
    )
    
    result = call_deepseek(prompt)
    if not result:
        return None
    
    confidence = result.get("confidence", 0)
    if confidence < 0.1:
        # AI 判断这不是发射任务新闻
        return None
    
    # 生成 timeline_id
    news_id = article.get("news_id", "")
    timeline_id = hashlib.md5(f"timeline_{news_id}".encode()).hexdigest()[:16]
    
    now = datetime.now().isoformat()
    
    return {
        "timeline_id": timeline_id,
        "rocket_id": result.get("rocket_id"),
        "mission_name": result.get("mission_name"),
        "launch_time": result.get("launch_time"),
        "launch_site": result.get("launch_site"),
        "payload": result.get("payload"),
        "outcome": result.get("outcome"),
        "reuse_status": result.get("reuse_status"),
        "brief_desc": result.get("brief_desc"),
        "related_news_ids": json.dumps([news_id]),
        "create_time": now,
        "update_time": now,
        "_confidence": confidence,
        "_source_news_id": news_id
    }


def process_pending_articles(
    category: str = "航空航天",
    limit: int = 20,
    auto_insert: bool = True,
    confidence_threshold: float = 0.7
) -> Dict:
    """
    处理待审核文章，提取时间线数据
    
    Args:
        category: 要处理的分类
        limit: 每次处理的最大文章数
        auto_insert: 是否自动插入高置信度结果
        confidence_threshold: 自动插入的置信度阈值
    
    Returns:
        处理结果统计
    """
    from app.database import get_supabase, upsert_launch_timeline, update_article_status
    
    sb = get_supabase()
    
    # 获取待处理文章
    result = sb.table("raw_articles").select("*").eq("category", category).eq("status", "pending").order("publish_time", desc=True).limit(limit).execute()
    articles = result.data
    
    if not articles:
        return {"processed": 0, "message": "没有待处理的文章"}
    
    stats = {
        "total": len(articles),
        "extracted": 0,
        "auto_inserted": 0,
        "pending_review": 0,
        "failed": 0,
        "results": []
    }
    
    for article in articles:
        news_id = article.get("news_id", "")
        print(f"  [AI] 处理: {article.get('title', '')[:50]}...")
        
        # AI 提取
        timeline_data = extract_timeline_from_article(article)
        
        if not timeline_data:
            print(f"  [AI] → 非发射任务新闻，跳过")
            # 标记为已处理（online）
            update_article_status(news_id, "online")
            stats["extracted"] += 0
            continue
        
        confidence = timeline_data.pop("_confidence", 0)
        source_news_id = timeline_data.pop("_source_news_id", "")
        
        print(f"  [AI] → 置信度: {confidence:.2f} | 任务: {timeline_data.get('mission_name', 'N/A')}")
        
        if auto_insert and confidence >= confidence_threshold:
            # 高置信度，自动插入
            success = upsert_launch_timeline(timeline_data)
            if success:
                update_article_status(news_id, "online")
                stats["auto_inserted"] += 1
                print(f"  [AI] → 自动入库 ✓")
            else:
                stats["failed"] += 1
                print(f"  [AI] → 入库失败 ✗")
        else:
            # 低置信度，标记待审核
            # TODO: 可以加一个 pending_review 状态
            stats["pending_review"] += 1
            print(f"  [AI] → 待人工审核")
        
        stats["extracted"] += 1
        stats["results"].append({
            "news_id": news_id,
            "title": article.get("title", "")[:60],
            "confidence": confidence,
            "mission_name": timeline_data.get("mission_name"),
            "auto_inserted": auto_insert and confidence >= confidence_threshold
        })
    
    return stats


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    
    print("=== AI 新闻提取 ===\n")
    result = process_pending_articles(limit=5)
    print(f"\n=== 完成 ===")
    print(f"总计: {result['total']} 条")
    print(f"提取成功: {result['extracted']} 条")
    print(f"自动入库: {result['auto_inserted']} 条")
    print(f"待审核: {result['pending_review']} 条")

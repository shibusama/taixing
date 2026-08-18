"""
AI 新闻结构化提取模块
从 raw_articles 中提取结构化要闻，写入 latest_news 表
支持所有板块
"""

import json
import hashlib
import os
import requests
from datetime import datetime
from typing import List, Dict, Optional

# Load .env config from project root (API key / base url / model)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"))
except Exception:
    pass

DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL", DEEPSEEK_BASE_URL + "/chat/completions")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# 板块映射
BOARD_MAP = {
    "rocket": "可回收火箭",
    "moon": "中美登月",
    "controlled-fusion": "可控核聚变",
    "semiconductor": "中国半导体",
    "china-tech": "中国科技AI",
    "mega-projects": "中国大工程",
    "finance": "科技资本",
}


def get_board_label(category: str) -> str:
    """将板块标识转为中文名"""
    return BOARD_MAP.get(category, category)


EXTRACTION_PROMPT = """你是科技新闻编辑助手。根据以下新闻内容，提取结构化信息：

新闻标题：{title}
新闻摘要：{summary}
新闻正文：{raw_content}
来源：{source_name}
发布时间：{publish_time}
所属板块：{category}

请输出 JSON 格式（只输出 JSON，不要其他内容）：
{{
  "title": "精炼后的标题（保留核心信息，不超过40字）",
  "summary": "一句话摘要（突出关键数字和进展，不超过80字）",
  "source": "来源名称（如 SpaceX、NASA、中芯国际、ITER 等，无法判断则为 null）",
  "publish_date": "发布日期（YYYY-MM-DD 格式，无法判断则为 null）",
  "link": "原文链接",
  "board_label": "板块中文名（如 可回收火箭、可控核聚变 等）",
  "confidence": 0.0到1.0之间的数字，表示本条新闻是否属于有效科技新闻
}}

注意：
1. 如果新闻内容与科技无关（如纯广告、活动通知、招聘信息），confidence 设为 0
2. title 要简洁精准，保留关键数字和实体名
3. summary 用中文，一句话说清核心进展
4. 日期格式统一为 YYYY-MM-DD，无法判断则返回 null
5. 只输出 JSON，不要 markdown 代码块标记"""


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


def extract_news_from_article(article: Dict) -> Optional[Dict]:
    """从单条新闻中提取结构化要闻"""
    category = article.get("category", "")
    prompt = EXTRACTION_PROMPT.format(
        title=article.get("title", ""),
        summary=article.get("summary", ""),
        raw_content=article.get("raw_content", "") or "",
        source_name=article.get("source_name", ""),
        publish_time=article.get("publish_time", ""),
        category=category,
    )

    result = call_deepseek(prompt)
    if not result:
        return None

    confidence = result.get("confidence", 0)
    if confidence < 0.1:
        return None

    now = datetime.now().isoformat()
    board_label = result.get("board_label") or get_board_label(category)

    return {
        "title": (result.get("title") or article.get("title", ""))[:100],
        "summary": (result.get("summary") or article.get("summary", ""))[:200],
        "source": result.get("source") or article.get("source_name", ""),
        "board": category,
        "board_label": board_label,
        "link": result.get("link") or article.get("source_url", ""),
        "publish_date": result.get("publish_date"),
        "is_active": True,
        "sort_order": 0,
        "created_at": now,
        "updated_at": now,
        "_confidence": confidence,
        "_article_news_id": article.get("news_id", ""),
    }


def _record_ai_extract_log(
    category: str,
    limit: int,
    total: int,
    inserted: int,
    failed: int,
    status: str,
    message: str = "",
):
    """写入 ai_extract_logs 历史记录（表不存在时容错，不影响主流程）"""
    try:
        from app.db.admin import log_ai_extract
        log_ai_extract(
            category=category,
            limit=limit,
            total=total,
            inserted=inserted,
            failed=failed,
            status=status,
            message=message,
        )
    except Exception as e:
        print(f"[AI] ai_extract_logs 记录失败（已忽略，不影响主流程）：{e}")



def process_pending_articles(
    category: str = None,
    limit: int = 20,
    auto_insert: bool = True,
    confidence_threshold: float = 0.6
) -> Dict:
    """
    处理待审核文章，提取结构化要闻写入 latest_news

    Args:
        category: 要处理的分类，None 表示所有板块
        limit: 每次处理的最大文章数
        auto_insert: 是否自动插入高置信度结果
        confidence_threshold: 自动插入的置信度阈值

    Returns:
        处理结果统计
    """
    from app.database import get_supabase, update_article_status

    sb = get_supabase()

    # 构建查询
    query = sb.table("raw_articles").select("*").eq("status", "pending").order("publish_time", desc=True).limit(limit)
    if category:
        query = query.eq("category", category)
    result = query.execute()
    articles = result.data

    if not articles:
        _record_ai_extract_log(category, limit, 0, 0, 0, "success", "没有待处理的文章")
        return {"processed": 0, "message": "没有待处理的文章"}

    stats = {
        "total": len(articles),
        "extracted": 0,
        "auto_inserted": 0,
        "pending_review": 0,
        "failed": 0,
        "skipped_duplicate": 0,
        "results": []
    }

    for article in articles:
        news_id = article.get("news_id", "")
        print(f"  [AI] 处理: {article.get('title', '')[:50]}...")

        # AI 提取
        news_data = extract_news_from_article(article)

        if not news_data:
            print(f"  [AI] → 非科技新闻，跳过")
            update_article_status(news_id, "online")
            stats["extracted"] += 0
            continue

        confidence = news_data.pop("_confidence", 0)
        article_news_id = news_data.pop("_article_news_id", "")

        print(f"  [AI] → 置信度: {confidence:.2f} | {news_data.get('title', 'N/A')}")

        if auto_insert and confidence >= confidence_threshold:
            # 高置信度，检查是否已存在（按 title + board 去重）
            existing = sb.table("latest_news").select("title").eq("title", news_data["title"]).eq("board", news_data["board"]).limit(1).execute()
            if existing.data:
                print(f"  [AI] → 已存在，跳过")
                stats["skipped_duplicate"] += 1
            else:
                # 插入 latest_news
                try:
                    sb.table("latest_news").insert(news_data).execute()
                    update_article_status(news_id, "online")
                    stats["auto_inserted"] += 1
                    print(f"  [AI] → 入库 OK")
                except Exception as e:
                    stats["failed"] += 1
                    print(f"  [AI] → 入库失败: {e}")
        else:
            stats["pending_review"] += 1
            print(f"  [AI] → 置信度不足，待审核")

        stats["extracted"] += 1
        stats["results"].append({
            "news_id": news_id,
            "title": article.get("title", "")[:60],
            "confidence": confidence,
            "summary": news_data.get("summary", "")[:60],
            "auto_inserted": auto_insert and confidence >= confidence_threshold
        })

    _record_ai_extract_log(
        category,
        limit,
        stats.get("total", 0),
        stats.get("auto_inserted", 0),
        stats.get("failed", 0),
        "success",
        f"提取 {stats.get('extracted', 0)} 条，自动入库 {stats.get('auto_inserted', 0)} 条，待审核 {stats.get('pending_review', 0)} 条，重复 {stats.get('skipped_duplicate', 0)} 条",
    )

    return stats


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

    print("=== AI 新闻提取 → latest_news ===\n")
    result = process_pending_articles(limit=10)
    print(f"\n=== 完成 ===")
    print(f"总计: {result['total']} 条")
    print(f"提取成功: {result['extracted']} 条")
    print(f"自动入库: {result['auto_inserted']} 条")
    print(f"跳过重复: {result.get('skipped_duplicate', 0)} 条")
    print(f"待审核: {result['pending_review']} 条")
    print(f"失败: {result['failed']} 条")

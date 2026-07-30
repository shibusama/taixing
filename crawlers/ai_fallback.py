"""
AI 兜底模块
当爬虫 API 失败时，用 AI 直接获取数据。
"""

import json
import re
import time

# 复用 http_utils 的速率限制
from crawlers.http_utils import _rate_limit


def fetch_ai_fallback(topic, count=10):
    """当爬虫 API 失败时，用 AI 直接获取数据"""
    try:
        from coze_coding_dev_sdk import LLMClient
        from langchain_core.messages import SystemMessage, HumanMessage
    except ImportError:
        print("[AI兜底] LLMClient 不可用，跳过")
        return []

    system_prompt = f"""你是一个科技新闻助手。列出{topic}领域最近的重要新闻，{count}条。
必须返回纯 JSON 数组，每项包含 title, summary, source, publish_date。
- title: 简洁标题（中文）
- summary: 一句话摘要（中文，包含关键信息）
- source: 来源（如 SpaceX、NASA 等）
- publish_date: 日期，格式 YYYY-MM-DD

要求：
1. 必须是真实事件，不要编造
2. 返回纯 JSON，不要加其他文字
3. 格式示例：[{{"title":"...","summary":"...","source":"...","publish_date":"2026-07-30"}}]"""

    try:
        _rate_limit()
        client = LLMClient()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"请列出{topic}领域最近的{count}条重要新闻，返回 JSON 数组。")
        ]
        response = client.invoke(
            messages=messages,
            model="doubao-seed-2-0-pro-260215",
            temperature=0.3,
            max_completion_tokens=4096
        )
        content = response.content
        if isinstance(content, list):
            content = " ".join(item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text")
        match = re.search(r"\[.*\]", content, re.DOTALL)
        if match:
            items = json.loads(match.group(0))
            print(f"[AI兜底] 获取 {len(items)} 条 {topic} 新闻")
            return items
    except Exception as e:
        print(f"[AI兜底] 失败: {e}")

    return []

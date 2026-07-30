"""
爬虫公共工具模块
所有爬虫模块共享的 HTTP 请求、JSON 读写、日期解析等工具函数。
"""

import json
import re
import os
import time
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# curl_cffi 用于绕过 TLS 指纹检测
try:
    from curl_cffi import requests as cffi_requests
    HAS_CFFI = True
except ImportError:
    HAS_CFFI = False

# 路径
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
}

# === 全局速率限制 ===
_last_request_time = 0.0
_MIN_REQUEST_INTERVAL = 2.0  # 每次请求至少间隔 2 秒


def _rate_limit():
    """确保两次请求之间至少间隔 _MIN_REQUEST_INTERVAL 秒"""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if 0 < elapsed < _MIN_REQUEST_INTERVAL:
        sleep_time = _MIN_REQUEST_INTERVAL - elapsed
        time.sleep(sleep_time)
    _last_request_time = time.time()


# === 限流保护的 HTTP 请求 ===

def _request_with_retry(method, url, **kwargs):
    """带限流和 429 自动重试的请求"""
    max_retries = kwargs.pop("retries", 3)
    # 从 kwargs 中提取可能重复的字段，用显式参数优先
    req_headers = kwargs.pop("headers", None) or HEADERS
    req_timeout = kwargs.pop("timeout", 15)
    last_error = None
    for attempt in range(max_retries):
        _rate_limit()
        try:
            resp = requests.request(method, url, timeout=req_timeout, headers=req_headers, verify=False, **kwargs)
            if resp.status_code == 429:
                print(f"[429] {url} 被限流，跳过")
                return None
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt == max_retries - 1:
                raise
            print(f"[retry] {url} 请求失败 ({e})，{5 * (attempt + 1)}s 后重试 ({attempt+1}/{max_retries})")
            time.sleep(5 * (attempt + 1))
    # 所有重试用完仍失败
    raise last_error or RuntimeError(f"请求失败: {url}")


def load_json(filename):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename, data):
    with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_meta(data):
    if "meta" in data:
        data["meta"]["updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")


def fetch_html(url, timeout=20, retries=3):
    """获取 HTML 内容（带限流，429 直接跳过）"""
    resp = _request_with_retry("GET", url, timeout=timeout, retries=retries)
    if resp is None:
        return None
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def fetch_html_cffi(url, timeout=20):
    """用 curl_cffi 伪装浏览器 TLS 指纹，绕过 Apache/WAF 的 403"""
    if not HAS_CFFI:
        raise RuntimeError("curl_cffi 未安装，请运行: pip install curl_cffi")
    _rate_limit()
    resp = cffi_requests.get(url, impersonate="chrome", timeout=timeout, verify=False)
    resp.raise_for_status()
    return resp.text


def fetch_json(url, params=None, timeout=15, retries=3, headers=None):
    """获取 JSON 数据（带限流，429 直接跳过）"""
    req_headers = headers or HEADERS
    resp = _request_with_retry("GET", url, params=params, timeout=timeout, retries=retries, headers=req_headers)
    if resp is None:
        return None
    return resp.json()


def parse_date(text):
    """尝试多种日期格式解析，返回 YYYY-MM-DD"""
    text = text.strip()
    formats = [
        "%Y-%m-%d", "%Y/%m/%d",
        "%B %d, %Y", "%b %d, %Y",
        "%B %d %Y", "%b %d %Y",
        "%Y年%m月%d日", "%Y.%m.%d",
        "%d %B %Y", "%d %b %Y",
        "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(text[:20], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
    if m:
        return m.group(0)
    m = re.search(r'(\w{3,9})\s+(\d{1,2}),?\s*(\d{4})', text)
    if m:
        try:
            return datetime.strptime(m.group(0).replace(",", ""), "%B %d %Y").strftime("%Y-%m-%d")
        except ValueError:
            try:
                return datetime.strptime(m.group(0).replace(",", ""), "%b %d %Y").strftime("%Y-%m-%d")
            except ValueError:
                pass
    return text[:30]


# === AI 兜底 ===

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

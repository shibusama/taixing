"""
HTTP 请求工具模块
提供限流保护的 HTTP 请求、HTML/JSON 获取、日期解析等功能。
"""

import re
import time
from datetime import datetime

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


def _request_with_retry(method, url, **kwargs):
    """带限流和 429 自动重试的请求"""
    max_retries = kwargs.pop("retries", 3)
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
    raise last_error or RuntimeError(f"请求失败: {url}")


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

"""
爬虫公共工具模块
所有爬虫模块共享的 HTTP 请求、JSON 读写、日期解析等工具函数。
"""

import json
import re
import os
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


def load_json(filename):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename, data):
    with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_meta(data):
    if "meta" in data:
        data["meta"]["updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")


def fetch_html(url, timeout=20):
    resp = requests.get(url, timeout=timeout, headers=HEADERS, verify=False)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text


def fetch_html_cffi(url, timeout=20):
    """用 curl_cffi 伪装浏览器 TLS 指纹，绕过 Apache/WAF 的 403"""
    if not HAS_CFFI:
        raise RuntimeError("curl_cffi 未安装，请运行: pip install curl_cffi")
    resp = cffi_requests.get(url, impersonate="chrome", timeout=timeout, verify=False)
    resp.raise_for_status()
    return resp.text


def fetch_json(url, params=None, timeout=15):
    resp = requests.get(url, params=params, timeout=timeout, headers=HEADERS, verify=False)
    resp.raise_for_status()
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

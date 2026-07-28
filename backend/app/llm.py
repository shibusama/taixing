"""
LLM 调用模块 — 爬虫后自动更新火箭板块引言

使用 OpenAI 兼容 API（支持 OpenAI / DeepSeek / 豆包等），
从环境变量读取凭据：
  - OPENAI_API_KEY   (必填)
  - OPENAI_BASE_URL  (可选，默认 https://api.openai.com/v1)
  - OPENAI_MODEL     (可选，默认 gpt-4o-mini)
"""

import os
import json
import requests
from app.database import get_rocket_companies

# ---- 配置 ----
API_KEY = os.environ.get("OPENAI_API_KEY", "")
BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def _build_prompt(companies: list) -> str:
    """根据火箭公司列表构建 prompt。"""
    lines = []
    for c in companies:
        lines.append(
            f"- {c['company']} / {c['rocket']}（{c['country']}）："
            f"回收方式 {c.get('recovery') or '待定'}，状态 {c.get('status') or '未知'}，"
            f"LEO 运力 {c.get('leo') or '未知'}，推力 {c.get('thrust') or '未知'}"
        )
    data_block = "\n".join(lines)

    return f"""你是「钛星」科技媒体平台的首席航天分析师。请根据以下全球可回收火箭公司的最新数据，
写两段中文引言（每段 1-2 句话），放在「可回收火箭 → 全球进展」页面顶部。

要求：
1. 第一段：用一个生动比喻（不用"黄金造一次性筷子"了，换个新的）说明可回收火箭的经济意义。
2. 第二段：概括当前全球格局（哪国领跑、哪国追赶、有什么新趋势），用 <strong> 标签强调关键短语。
3. 语言精炼有力，不堆数据，读者看完知道"现在什么格局"即可。
4. 输出纯 HTML：每段用 <p>...</p> 包裹，两段之间换行，不要 markdown 标记。

当前火箭数据：
{data_block}

直接输出 HTML 片段（两段 <p>）："""


def generate_rocket_intro() -> str | None:
    """调用 LLM 根据最新 rocket_companies 数据生成引言。

    返回生成的 HTML 文本，失败返回 None。
    """
    if not API_KEY:
        return None

    # 1. 读取火箭数据
    companies = get_rocket_companies()

    if not companies:
        return None

    # 2. 构建 prompt
    prompt = _build_prompt(companies)

    # 3. 调用 LLM
    try:
        resp = requests.post(
            f"{BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": "你是钛星科技媒体的航天分析师，输出精炼的中文 HTML。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 500,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return None
        text = resp.json()["choices"][0]["message"]["content"].strip()
        # 清理可能的 markdown 标记
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("\n```", 1)[0].strip()
        return text
    except Exception:
        return None


def update_rocket_intro_if_needed() -> bool:
    """如果 OPENAI_API_KEY 已配置，调用 LLM 生成新引言并写入数据库。

    返回 True 表示已更新。
    """
    if not API_KEY:
        return False

    intro = generate_rocket_intro()
    if not intro:
        return False

    from app.database import set_rocket_intro
    set_rocket_intro(intro)
    return True

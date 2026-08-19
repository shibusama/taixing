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


# ========================================================================
# DeepSeek 版：发射计划页「下一次发射评价」引言
# ========================================================================

import os  # noqa: E402
from datetime import datetime  # noqa: E402

DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL", DEEPSEEK_BASE_URL + "/chat/completions")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
_DEEPSEEK_KEY_CACHED = None


def _get_deepseek_key() -> str:
    """读取 DeepSeek key：优先环境变量 DEEPSEEK_API_KEY，否则读 DSH 配置 ~/.dsh/.credentials.yaml（本地开发）"""
    global _DEEPSEEK_KEY_CACHED
    if _DEEPSEEK_KEY_CACHED is not None:
        return _DEEPSEEK_KEY_CACHED
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        try:
            from pathlib import Path
            import yaml
            home = Path.home()
            creds_file = home / ".dsh" / ".credentials.yaml"
            if creds_file.exists():
                data = yaml.safe_load(creds_file.read_text(encoding="utf-8")) or {}
                key = data.get("DEEPSEEK_API_KEY", "")
        except Exception:
            key = ""
    _DEEPSEEK_KEY_CACHED = key
    return key


def _call_deepseek_text(prompt: str) -> str | None:
    """调用 DeepSeek 返回纯文本（用于引言生成）。失败返回 None 并打印日志。"""
    key = _get_deepseek_key()
    if not key:
        print(f"[AI][{datetime.now().isoformat()}] rocket_next_intro 生成失败: 未配置 DEEPSEEK_API_KEY")
        return None
    try:
        resp = requests.post(
            DEEPSEEK_API_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": DEEPSEEK_MODEL,
                "messages": [
                    {"role": "system", "content": "你是钛星科技媒体的航天分析师，输出精炼的中文。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 500,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"[AI][{datetime.now().isoformat()}] rocket_next_intro 生成失败: HTTP {resp.status_code} {resp.text[:200]}")
            return None
        text = resp.json()["choices"][0]["message"]["content"].strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("\n```", 1)[0].strip()
        return text
    except Exception as e:
        print(f"[AI][{datetime.now().isoformat()}] rocket_next_intro 生成失败: {e}")
        return None


def _build_next_launch_prompt(launch: dict) -> str:
    """根据下一条即将发射的事件构建 prompt。"""
    return f"""你是「钛星」科技媒体的航天分析师。请针对下面这次【下一次即将发射的火箭任务】写一段中文评述（3-4 句话），放在「可回收火箭 → 发射计划」页面顶部。

要求覆盖：
1. 这次发射的目的是什么
2. 主要验证什么功能 / 技术
3. 如果成功意味着什么（里程碑/标志意义）
4. 有什么愿景 / 后续影响

要求：
- 语言精炼有力，客观专业，不堆砌数据
- 围绕"这次发射"本身，不要泛泛而谈
- 输出纯文本（1 段，不要 markdown、不要 <p> 标签）

发射事件信息：
- 火箭/任务：{launch.get('mission_name') or '未知'}
- 发射时间：{launch.get('launch_time') or '未知'}
- 发射场：{launch.get('launch_site') or '未知'}
- 载荷：{launch.get('payload') or '未知'}
- 状态：{launch.get('outcome') or '未知'}
- 简介：{launch.get('brief_desc') or '无'}

直接输出评述："""


def generate_next_launch_intro() -> str | None:
    """基于 rocket_launch_timeline 里最近一条「即将发射」事件，生成发射评价引言。

    返回生成的文本，失败返回 None（不覆盖旧值）。
    """
    from app.database import get_launch_timeline
    from datetime import datetime as _dt

    timeline = get_launch_timeline(limit=200) or []
    now = _dt.now()
    # 找最近的「计划中 / To Be Determined」且时间 >= 今天的发射
    upcoming = [it for it in timeline if it.get("launch_time")]
    upcoming = [it for it in upcoming if _dt.fromisoformat(it["launch_time"].replace("T", " ")[:19]) >= now]
    if not upcoming:
        print(f"[AI][{_dt.now().isoformat()}] rocket_next_intro 生成失败: 没有找到即将发射的事件")
        return None
    # 取最近一条（按时间排序后第一条）
    upcoming.sort(key=lambda x: x["launch_time"])
    target = upcoming[0]
    prompt = _build_next_launch_prompt(target)
    return _call_deepseek_text(prompt)


def update_rocket_next_intro_if_needed() -> bool:
    """爬虫后调用：生成「下一次发射评价」引言并写入 board_status.rocket_next_intro。

    生成失败时保留旧值（不覆盖），仅记录日志。返回 True 表示成功更新。
    """
    from app.database import get_rocket_next_intro, set_rocket_next_intro

    intro = generate_next_launch_intro()
    if not intro:
        # 失败：不覆盖旧值，日志已由 _call_deepseek_text 打印
        print(f"[AI][{datetime.now().isoformat()}] rocket_next_intro 未更新（保留旧值）")
        return False

    set_rocket_next_intro(intro)
    print(f"[AI][{datetime.now().isoformat()}] rocket_next_intro 已更新: {intro[:60]}...")
    return True


# ========================================================================
# 「最近一期发射任务总结」（已发射，有结果）
# ========================================================================

def _build_last_review_prompt(launch: dict) -> str:
    """根据最近一期已发射任务构建总结 prompt。"""
    return f"""你是「钛星」科技媒体的航天分析师。请针对下面这次【最近一期已经发射的火箭任务】写一段中文总结（3-4 句话），放在「可回收火箭 → 发射计划」页面顶部、下一次发射评价的上方。

要求覆盖：
1. 这次发射的结果（成功 / 失败 / 部分成功）
2. 成功意味着什么（里程碑 / 突破了什么技术 / 标志意义）；若失败则说明失败的影响与后续
3. 这次发射验证了什么技术 / 工程能力
4. 后续的愿景 / 影响（如进入工程化复用阶段、复飞计划、商业意义等）

要求：
- 语言精炼有力，客观专业，不堆砌数据
- 围绕"这次发射"本身，不要泛泛而谈
- 输出纯文本（1 段，不要 markdown、不要 <p> 标签）

发射事件信息：
- 火箭/任务：{launch.get('mission_name') or '未知'}
- 发射时间：{launch.get('launch_time') or '未知'}
- 发射场：{launch.get('launch_site') or '未知'}
- 载荷：{launch.get('payload') or '未知'}
- 结果：{launch.get('outcome') or '未知'}
- 简介：{launch.get('brief_desc') or '无'}

直接输出总结："""


def generate_last_launch_review() -> str | None:
    """基于 rocket_launch_timeline 里最近一期「已发射」事件（有明确结果），生成发射总结。

    返回生成的文本，失败返回 None（不覆盖旧值）。
    """
    from app.database import get_launch_timeline
    from datetime import datetime as _dt

    timeline = get_launch_timeline(limit=300) or []
    now = _dt.now()
    done = []
    for it in timeline:
        lt = it.get("launch_time")
        outcome = it.get("outcome") or ""
        if not lt:
            continue
        try:
            d = _dt.fromisoformat(lt.replace("T", " ")[:19])
        except Exception:
            continue
        # 已发射且有明确结果（成功/失败/部分成功），时间 <= 今天
        if d <= now and outcome in ("成功", "失败", "部分成功"):
            done.append(it)
    if not done:
        print(f"[AI][{_dt.now().isoformat()}] rocket_last_review 生成失败: 没有找到已发射且有结果的事件")
        return None
    done.sort(key=lambda x: x["launch_time"])
    target = done[-1]  # 最近一期（时间最新）
    prompt = _build_last_review_prompt(target)
    return _call_deepseek_text(prompt)


def update_rocket_last_review_if_needed() -> bool:
    """爬虫后调用：生成「最近一期发射总结」并写入 board_status.rocket_last_review。

    生成失败时保留旧值（不覆盖），仅记录日志。返回 True 表示成功更新。
    """
    from app.database import set_rocket_last_review

    review = generate_last_launch_review()
    if not review:
        print(f"[AI][{datetime.now().isoformat()}] rocket_last_review 未更新（保留旧值）")
        return False

    set_rocket_last_review(review)
    print(f"[AI][{datetime.now().isoformat()}] rocket_last_review 已更新: {review[:60]}...")
    return True

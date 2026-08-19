"""
宏观指标监控板块爬虫 — 债务/利率/国债/汇率/大宗商品/股指期货

数据写入 data/macro.json（与页面 macro.html 对应）。
低频数据（FOMC 日程、美联储成员、债务规模、利息警戒线）保持人工维护，
本模块只更新高频行情数据。

数据源策略：
- 美联储利率 / 美债收益率 / 原油 / 黄金：FRED API（需 FRED_API_KEY 环境变量）
- 日本央行利率 / 日本国债：FRED（可公开，无 key 时部分可用）
- 中国 LPR：网页抓取（中国货币网）
- 中国国债：网页抓取（中债登 chinabond.com.cn）
- 汇率：Frankfurter API（ECB）
- 美股股指期货：Yahoo Finance 行情 API
- 中国股指期货：东方财富期货行情
"""

import os
import re
from datetime import datetime

from bs4 import BeautifulSoup

from .utils import (
    fetch_html, fetch_html_cffi, fetch_json, load_json, save_json, update_meta,
)

# FRED API 基础 URL
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# FRED 系列映射
FRED_SERIES = {
    "fed_rate": "FEDFUNDS",          # 美国联邦基金利率（目标区间中间值）
    "us_treasury_2y": "DGS2",        # 美债 2 年
    "us_treasury_10y": "DGS10",      # 美债 10 年
    "us_treasury_20y": "DGS20",      # 美债 20 年
    "us_treasury_30y": "DGS30",      # 美债 30 年
    "jp_treasury_10y": "IRLTLT01JPM156N",  # 日本 10 年国债
    "jp_treasury_20y": "IRLTLT01JPM156N",  # 日本长端（FRED 无 20 年，用 10 年近似，人工核对）
    "oil_wti": "DCOILWTICO",         # WTI 原油
    # 黄金：FRED 系列已移除，改用 Yahoo GC=F（COMEX 黄金期货）
}


def _fred_get(series_id, limit=1):
    """从 FRED 取最新观测值，返回 (value, date)；无 key 或失败返回 (None, None)"""
    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        print(f"  [FRED] 未配置 FRED_API_KEY，跳过 {series_id}")
        return None, None
    try:
        data = fetch_json(FRED_BASE, params={
            "series_id": series_id, "api_key": api_key,
            "file_type": "json", "limit": limit, "sort_order": "desc",
        })
        if data is None:
            return None, None
        obs = data.get("observations", [])
        if not obs:
            return None, None
        return obs[0].get("value"), obs[0].get("date")
    except Exception as e:
        print(f"  [FRED] {series_id} 请求失败: {e}")
        return None, None


def _load_macro():
    """加载 macro.json，失败则报错返回 None"""
    try:
        return load_json("macro.json")
    except Exception as e:
        print(f"  [宏观] 无法加载 macro.json: {e}")
        return None


# ================= ① 央行基准利率 =================

def crawl_fed_rate():
    """美联储利率 → macro.json rates.policy_rates[美联储]"""
    print("\n[美联储利率] 从 FRED 抓取...")
    macro = _load_macro()
    if macro is None:
        return None
    value, date = _fred_get(FRED_SERIES["fed_rate"])
    if value is None or value == ".":
        print("  [美联储利率] 未获取到数据，跳过")
        return None
    # FRED 返回目标区间中间值（如 3.625），页面格式为区间 "3.50—3.75%"
    try:
        mid = float(value)
        half = 0.125
        lo, hi = mid - half, mid + half
        text = f"{lo:.2f}—{hi:.2f}%"
    except (TypeError, ValueError):
        text = f"{value}%"
    for item in macro.get("rates", {}).get("policy_rates", []):
        if "美联储" in item.get("label", ""):
            item["value"] = text
            item["sub"] = f"FRED 更新于 {date}"
            print(f"  美联储利率 → {text}")
            break
    update_meta(macro)
    save_json("macro.json", macro)
    print("  [美联储利率] macro.json 已更新 ✓")
    return {"rate": text, "date": date}


def crawl_japan_rate():
    """日本央行利率 → macro.json rates.policy_rates[日元利率]"""
    print("\n[日本利率] 从 FRED 抓取...")
    macro = _load_macro()
    if macro is None:
        return None
    # FRED 无日本政策利率直接序列，尝试用短期国债收益率近似或跳过
    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        print("  [日本利率] 未配置 FRED_API_KEY，跳过（人工维护）")
        return None
    # 用日本 1 年期国债作为参考（无政策利率序列）
    value, date = _fred_get("IRLTLT01JPM156N")
    if value is None or value == ".":
        print("  [日本利率] 未获取到数据，跳过")
        return None
    for item in macro.get("rates", {}).get("policy_rates", []):
        if "日元" in item.get("label", ""):
            try:
                item["value"] = f"{float(value):.2f}%"
            except (TypeError, ValueError):
                item["value"] = f"{value}%"
            item["sub"] = f"日本央行 · 数据截至 {date}（人工核对）"
            print(f"  日本利率参考 → {item['value']}")
            break
    update_meta(macro)
    save_json("macro.json", macro)
    print("  [日本利率] macro.json 已更新 ✓")
    return {"rate": value, "date": date}


def crawl_cn_lpr():
    """中国 LPR → macro.json rates.policy_rates[中国LPR]

    LPR 每月 20 日由央行公布一次，属低频数据；且中国货币网接口已失效、
    免费可靠接口缺失，因此保持人工维护。此函数仅提示，不自动写入。
    """
    print("\n[中国LPR] 每月公布一次（低频），保持人工维护，跳过自动抓取")
    return None


# ================= ② 国债收益率 =================

def crawl_treasury_yields():
    """国债收益率 → macro.json rates.bonds（美/日 FRED + 中 中债登）"""
    print("\n[国债收益率] 抓取美日 FRED + 中国中债登...")
    macro = _load_macro()
    if macro is None:
        return None
    bonds = macro.get("rates", {}).get("bonds", [])
    if not bonds:
        print("  [国债收益率] macro.json 无 bonds 结构，跳过")
        return None

    # --- 美国：FRED DGS2/DGS10/DGS20/DGS30 ---
    us = next((b for b in bonds if b.get("country") == "美国"), None)
    if us:
        us_y2, _ = _fred_get(FRED_SERIES["us_treasury_2y"])
        us_y10, _ = _fred_get(FRED_SERIES["us_treasury_10y"])
        us_y20, _ = _fred_get(FRED_SERIES["us_treasury_20y"])
        us_y30, _ = _fred_get(FRED_SERIES["us_treasury_30y"])
        if us_y2: us["y2"] = f"{float(us_y2):.2f}%"
        if us_y10: us["y10"] = f"{float(us_y10):.2f}%"
        if us_y20: us["y20"] = f"{float(us_y20):.2f}%"
        if us_y30: us["y30"] = f"{float(us_y30):.2f}%"
        print(f"  美国: 2Y={us['y2']} 10Y={us['y10']} 20Y={us['y20']} 30Y={us['y30']}")

    # --- 日本：FRED ---
    jp = next((b for b in bonds if b.get("country") == "日本"), None)
    if jp:
        jp_y10, _ = _fred_get(FRED_SERIES["jp_treasury_10y"])
        if jp_y10:
            jp["y10"] = f"{jp_y10}%"
        print(f"  日本: 10Y={jp.get('y10', 'N/A')}（仅 10Y，其余人工维护）")

    # --- 中国：中债登网页抓取（提供 10年/30年，2年/20年人工维护） ---
    cn = next((b for b in bonds if b.get("country") == "中国"), None)
    if cn:
        try:
            cn_val = _fetch_china_bond_yields()
            if cn_val:
                if cn_val.get("y10"):
                    cn["y10"] = cn_val["y10"]
                if cn_val.get("y30"):
                    cn["y30"] = cn_val["y30"]
                print(f"  中国: 10Y={cn.get('y10')} 30Y={cn.get('y30')}（2Y/20Y 人工维护）")
        except Exception as e:
            print(f"  [中国国债] 抓取失败: {e}")

    update_meta(macro)
    save_json("macro.json", macro)
    print("  [国债收益率] macro.json 已更新 ✓")
    return {"us": us, "jp": jp, "cn": cn}


def _fetch_china_bond_yields():
    """从中债登官网抓取中国国债收益率曲线（提供 10年/30年）"""
    from bs4 import BeautifulSoup
    url = "https://yield.chinabond.com.cn/cbweb-cbrc-web/cbrc/showCbrc"
    try:
        html = fetch_html_cffi(url, timeout=20) or fetch_html(url, timeout=20)
    except Exception:
        html = fetch_html(url, timeout=20)
    if not html:
        print("  [中国国债] 页面获取失败")
        return None
    try:
        soup = BeautifulSoup(html, "lxml")
        rows = soup.find_all("tr")
        # 第一步：从表头行确定 "10年"/"30年" 所在列索引
        header_cells = None
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if cells and any(l in cells for l in ("10年", "30年")):
                header_cells = cells
                break
        if not header_cells:
            print("  [中国国债] 未找到含 10年/30年 的表头")
            return None
        col_idx = {}
        for label in ("10年", "30年"):
            if label in header_cells:
                col_idx[label] = header_cells.index(label)
        # 第二步：在 "Government Bond"（国债）数据行取值
        result = {}
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if not cells:
                continue
            joined = " ".join(cells)
            if "Government Bond" in joined or "国债" in joined:
                for label, idx in col_idx.items():
                    if idx < len(cells):
                        try:
                            val = float(cells[idx])
                            result["y10" if label == "10年" else "y30"] = f"{val:.4f}%"
                        except (ValueError, TypeError):
                            pass
                break
        if result:
            print(f"  [中国国债] 中债登解析成功: {result}")
            return result
        print("  [中国国债] 未解析到国债收益率行")
        return None
    except Exception as e:
        print(f"  [中国国债] 解析失败: {e}")
        return None


# ================= ③ 外汇汇率 =================

def crawl_fx():
    """汇率 → macro.json rates.fx（Frankfurter/ECB）"""
    print("\n[汇率] 抓取 Frankfurter API (ECB)...")
    macro = _load_macro()
    if macro is None:
        return None
    try:
        latest = fetch_json("https://api.frankfurter.app/latest",
                            params={"from": "USD", "to": "JPY,CNY"})
        if latest is None:
            print("  [汇率] API 不可用，跳过")
            return None
        rates = latest.get("rates", {})
        date = latest.get("date", "")
        jpy = rates.get("JPY")
        cny = rates.get("CNY")
        if not jpy or not cny:
            print("  [汇率] 未获取到 JPY/CNY，跳过")
            return None

        # 昨日对比计算涨跌（首次从占位转真实时只填价，不显示假涨跌）
        fx_items = macro.get("rates", {}).get("fx", [])
        for item in fx_items:
            if "日元" in item.get("name", ""):
                old_str = str(item.get("value", "")).replace(",", "").replace("%", "")
                try:
                    old_val = float(old_str)
                except ValueError:
                    old_val = 0
                if old_val <= 0:
                    item["value"] = f"{jpy:.2f}"
                    item["change"] = "--"
                    item["trend"] = "stable"
                    item["note"] = f"ECB 更新于 {date}"
                    print(f"  USD/JPY = {jpy:.2f}（首次获取）")
                else:
                    change = ((jpy - old_val) / old_val * 100)
                    item["value"] = f"{jpy:.2f}"
                    item["change"] = f"{'+' if change >= 0 else ''}{change:.2f}%"
                    item["trend"] = "up" if change >= 0 else "down"
                    item["note"] = f"ECB 更新于 {date}"
                    print(f"  USD/JPY = {jpy:.2f} ({item['change']})")
            elif "人民币" in item.get("name", ""):
                old_str = str(item.get("value", "")).replace(",", "").replace("%", "")
                try:
                    old_val = float(old_str)
                except ValueError:
                    old_val = 0
                if old_val <= 0:
                    item["value"] = f"{cny:.4f}"
                    item["change"] = "--"
                    item["trend"] = "stable"
                    item["note"] = f"ECB 更新于 {date}"
                    print(f"  USD/CNY = {cny:.4f}（首次获取）")
                else:
                    change = ((cny - old_val) / old_val * 100)
                    item["value"] = f"{cny:.4f}"
                    item["change"] = f"{'+' if change >= 0 else ''}{change:.2f}%"
                    item["trend"] = "up" if change >= 0 else "down"
                    item["note"] = f"ECB 更新于 {date}"
                    print(f"  USD/CNY = {cny:.4f} ({item['change']})")

        update_meta(macro)
        save_json("macro.json", macro)
        print("  [汇率] macro.json 已更新 ✓")
        return {"usd_jpy": jpy, "usd_cny": cny}
    except Exception as e:
        print(f"  [汇率] 失败: {e}")
        return None


# ================= ④ 大宗商品 =================

def crawl_commodities():
    """大宗商品 → macro.json commodities[大宗商品]（原油、黄金，FRED）"""
    print("\n[大宗商品] 从 FRED 抓取原油/黄金...")
    macro = _load_macro()
    if macro is None:
        return None
    groups = macro.get("commodities", {}).get("groups", [])
    goods = next((g for g in groups if g.get("name") == "大宗商品"), None)
    if not goods:
        print("  [大宗商品] 未找到 大宗商品 分组，跳过")
        return None

    oil, oil_date = _fred_get(FRED_SERIES["oil_wti"])
    gold_quote = _fetch_yahoo_quote("GC=F")   # 黄金：Yahoo COMEX 期货（FRED 黄金系列已移除）
    for item in goods.get("items", []):
        if item.get("name") == "原油":
            if oil:
                item["price"] = f"{float(oil):.2f}"
                item["unit"] = "美元/桶"
                item["note"] = f"WTI · FRED {oil_date}"
                print(f"  原油 = {item['price']} 美元/桶")
        elif item.get("name") == "黄金":
            if gold_quote:
                item["price"] = f"{gold_quote['price']:,.0f}"
                item["unit"] = "美元/盎司"
                item["change"] = gold_quote["change_pct"]
                item["trend"] = "up" if gold_quote["change_pct"].startswith("+") else "down"
                item["note"] = f"COMEX 黄金期货 · {gold_quote['date']}"
                print(f"  黄金 = {item['price']} 美元/盎司 ({item['change']})")

    update_meta(macro)
    save_json("macro.json", macro)
    print("  [大宗商品] macro.json 已更新 ✓")
    return {"oil": oil, "gold": gold_quote}


# ================= ⑤ 股指期货 =================

def crawl_futures():
    """股指期货 → macro.json commodities[美股/中国股指]"""
    print("\n[股指期货] 抓取美股期货 (Yahoo) + 中国股指期货 (东方财富)...")
    macro = _load_macro()
    if macro is None:
        return None
    groups = macro.get("commodities", {}).get("groups", [])

    # --- 美股期货：Yahoo Finance ---
    us_group = next((g for g in groups if g.get("name") == "美股股指期货"), None)
    if us_group:
        symbols = {"道琼斯期货": "YM=F", "标普500期货": "ES=F", "纳斯达克100期货": "NQ=F"}
        for item in us_group.get("items", []):
            sym = symbols.get(item.get("name"))
            if sym:
                quote = _fetch_yahoo_quote(sym)
                if quote:
                    item["price"] = f"{quote['price']:,.0f}"
                    item["unit"] = "点"
                    item["change"] = quote["change_pct"]
                    item["trend"] = "up" if quote["change_pct"].startswith("+") else "down"
                    item["note"] = f"Yahoo Finance {quote['date']}"
                    print(f"  {item['name']} = {item['price']} ({item['change']})")

    # --- 中国股指期货：东方财富 ---
    cn_group = next((g for g in groups if g.get("name") == "中国股指期货"), None)
    if cn_group:
        try:
            quotes = _fetch_eastmoney_futures()
            for item in cn_group.get("items", []):
                name = item.get("name", "")
                key = "IF" if "IF" in name else ("IC" if "IC" in name else None)
                if key and key in quotes:
                    item["price"] = quotes[key]["price"]
                    item["unit"] = "点"
                    item["change"] = quotes[key]["change"]
                    item["trend"] = quotes[key]["trend"]
                    item["note"] = "东方财富 · 主力合约"
                    print(f"  {item['name']} = {item['price']} ({item['change']})")
        except Exception as e:
            print(f"  [中国股指期货] 抓取失败: {e}")

    update_meta(macro)
    save_json("macro.json", macro)
    print("  [股指期货] macro.json 已更新 ✓")
    return True


def _fetch_yahoo_quote(symbol):
    """从 Yahoo Finance 获取行情（quote API）"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
        data = fetch_json(url)
        if not data or "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
            return None
        result = data["chart"]["result"][0]
        meta = result.get("meta", {})
        price = meta.get("regularMarketPrice")
        prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
        if price is None:
            return None
        change_pct = ""
        if prev_close:
            chg = (price - prev_close) / prev_close * 100
            change_pct = f"{'+' if chg >= 0 else ''}{chg:.1f}%"
        date = datetime.now().strftime("%Y-%m-%d")
        return {"price": price, "change_pct": change_pct, "date": date}
    except Exception as e:
        print(f"  [Yahoo] {symbol} 失败: {e}")
        return None


def _fetch_eastmoney_futures():
    """从新浪抓取中国股指期货主力合约行情（IF/IC）"""
    # 新浪国内期货接口：hq.sinajs.cn/list=nf_IF0（内盘期货主力连续）
    # 字段: [0]买价 [1]卖价 [2]最新价 [3]昨结算 [7]昨收 ...
    import requests
    result = {}
    try:
        url = "https://hq.sinajs.cn/list=nf_IF0,nf_IC0"
        headers = {"Referer": "https://finance.sina.com.cn/futures/"}
        resp = requests.get(url, headers=headers, timeout=15, verify=False)
        resp.encoding = "gbk"
        html = resp.text
        if not html:
            return result
        for code, key in [("nf_IF0", "IF"), ("nf_IC0", "IC")]:
            m = re.search(rf'hq_str_{code}="([^"]*)"', html)
            if not m:
                continue
            fields = m.group(1).split(",")
            if len(fields) < 8:
                continue
            try:
                last = float(fields[2])      # 最新价
                prev = float(fields[7])      # 昨收
            except (ValueError, TypeError):
                continue
            if last <= 0:
                continue
            change_pct = ((last - prev) / prev * 100) if prev else 0
            if abs(change_pct) > 15:        # 合理性校验
                continue
            trend = "up" if change_pct >= 0 else "down"
            sign = "+" if change_pct >= 0 else ""
            result[key] = {
                "price": f"{last:,.1f}",
                "change": f"{sign}{change_pct:.2f}%",
                "trend": trend,
            }
    except Exception as e:
        print(f"  [新浪期货] 请求失败: {e}")
    return result

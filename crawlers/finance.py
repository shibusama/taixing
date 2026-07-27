"""
金融板块爬虫 — 汇率 & 美联储利率
"""

import os
from datetime import datetime, timedelta

from bs4 import BeautifulSoup

from .utils import (
    fetch_html, fetch_json, load_json, save_json, update_meta,
)


def crawl_exchange_rates():
    """汇率 → 自动写入 finance.json"""
    print("\n[汇率] 抓取 Frankfurter API (ECB)...")
    try:
        latest = fetch_json("https://api.frankfurter.app/latest",
                            params={"from": "USD", "to": "JPY,CNY,EUR,GBP,CHF"})
        rates = latest.get("rates", {})
        date = latest.get("date", "")
        jpy = rates.get("JPY")
        if not jpy:
            print("  [汇率] 未获取到 JPY，跳过")
            return None

        # 昨日汇率
        prev_jpy = jpy
        try:
            yesterday = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
            prev = fetch_json(f"https://api.frankfurter.app/{yesterday}",
                              params={"from": "USD", "to": "JPY"})
            prev_jpy = prev.get("rates", {}).get("JPY", jpy)
        except:
            pass

        change_pct = ((jpy - prev_jpy) / prev_jpy * 100) if prev_jpy else 0
        print(f"  USD/JPY = {jpy:.2f} ({'+' if change_pct>=0 else ''}{change_pct:.2f}%)")

        # 写入 finance.json
        finance = load_json("finance.json")
        now_cn = datetime.now()
        finance["fx_highlights"][0]["num"] = f"{jpy:.2f}"
        finance["fx_highlights"][0]["sub"] = f"{now_cn.month}月{now_cn.day:02d}日实时"

        # 月高低
        try:
            end_date = datetime.strptime(date, "%Y-%m-%d")
            start_date = end_date - timedelta(days=30)
            monthly = fetch_json(
                f"https://api.frankfurter.app/{start_date.strftime('%Y-%m-%d')}..{date}",
                params={"from": "USD", "to": "JPY"})
            vals = [v["JPY"] for v in monthly.get("rates", {}).values() if "JPY" in v]
            if vals:
                finance["fx_highlights"][1]["num"] = f"{max(vals):.2f}"
                finance["fx_highlights"][2]["num"] = f"{min(vals):.2f}"
        except:
            pass

        # 年涨幅
        try:
            year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            year_data = fetch_json(f"https://api.frankfurter.app/{year_ago}",
                                   params={"from": "USD", "to": "JPY"})
            year_jpy = year_data.get("rates", {}).get("JPY", jpy)
            year_change = ((jpy - year_jpy) / year_jpy * 100)
            finance["fx_highlights"][3]["num"] = f"{'+' if year_change>=0 else ''}{year_change:.2f}<span class='unit'>%</span>"
        except:
            pass

        # 当日汇率行
        sign = "+" if change_pct >= 0 else ""
        finance["fx_rates"]["grid"][0]["v"] = f"{jpy:.3f} <em>{sign}{change_pct:.2f}%</em>"
        update_meta(finance)
        save_json("finance.json", finance)
        print(f"  [汇率] finance.json 已更新 ✓")
        return {"usd_jpy": jpy, "change_pct": change_pct}
    except Exception as e:
        print(f"  [汇率] 失败: {e}")
        return None


def crawl_fed_rate():
    """美联储利率 → 从 FRED 或网页抓取"""
    print("\n[美联储] 抓取利率数据...")
    try:
        fred_key = os.environ.get("FRED_API_KEY", "")
        if fred_key:
            data = fetch_json("https://api.stlouisfed.org/fred/series/observations",
                              params={"series_id": "FEDFUNDS", "api_key": fred_key,
                                      "file_type": "json", "limit": 1, "sort_order": "desc"})
            obs = data.get("observations", [{}])[0]
            rate = obs.get("value", "")
            date = obs.get("date", "")
            print(f"  美联储基金利率: {rate}% (截至 {date})")
            return {"rate": rate, "date": date}
        else:
            html = fetch_html("https://fred.stlouisfed.org/series/FEDFUNDS")
            soup = BeautifulSoup(html, "lxml")
            value_elem = soup.find(class_=lambda c: c and "value" in str(c).lower())
            if value_elem:
                print(f"  美联储基金利率: {value_elem.get_text(strip=True)}")
            print("  提示: 设置 FRED_API_KEY 环境变量可获取精确数据")
            return None
    except Exception as e:
        print(f"  [美联储] 失败: {e}")
        return None

"""
APScheduler — 定时爬虫调度
每小时自动全量爬一次 + AI 解读 + 同步 SQLite
"""
import sys, os, traceback
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.routers.api import run_crawler, CRAWLER_MODULES
from app.database import log_crawl

# 确保项目根目录可导入 ai_update 等模块
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # taixing/
sys.path.insert(0, str(PROJECT_ROOT))

scheduler = BackgroundScheduler(timezone="Asia/Shanghai")


def crawl_all_job():
    """定时任务：仅抓取全部7个板块"""
    for bid in CRAWLER_MODULES:
        try:
            run_crawler(bid)
            log_crawl(bid, "success", "Scheduled crawl OK")
        except Exception as e:
            log_crawl(bid, "failed", str(e))


def crawl_and_ai_job():
    """定时任务：抓取 → AI 解读 JSON → 同步 SQLite"""
    print(f"\n[scheduler] === 爬虫 + AI 解读 开始 ===")
    # 1. 抓取全部板块
    crawl_all_job()
    # 2. AI 解读 JSON 文件
    try:
        import ai_update
        result = ai_update.run_ai_update(base_dir=str(PROJECT_ROOT))
        print(f"[scheduler] AI 解读完成: success={result['success']}, fail={result['fail']}")
    except Exception as e:
        print(f"[scheduler] AI 解读失败: {e}")
        traceback.print_exc()
    # 3. 同步 JSON 到 SQLite
    try:
        from app.database import re_sync_all_from_json
        re_sync_all_from_json()
        print(f"[scheduler] SQLite 同步完成")
    except Exception as e:
        print(f"[scheduler] SQLite 同步失败: {e}")
        traceback.print_exc()


def start_scheduler():
    # 每小时整点抓取 + AI 解读 + 同步（避开凌晨 2-6 点）
    scheduler.add_job(
        crawl_and_ai_job,
        trigger=CronTrigger(minute=0, hour="7-23"),
        id="hourly_crawl_ai",
        name="每小时爬虫+AI解读+同步",
        replace_existing=True,
    )
    scheduler.start()


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)

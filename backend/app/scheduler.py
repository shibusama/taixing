"""
APScheduler - 定时爬虫调度
每小时自动全量爬一次（7个板块）
"""
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.services.crawler_service import run_crawler
from crawlers.crawler_registry import CRAWLER_MODULES
from app.database import log_crawl

scheduler = BackgroundScheduler(timezone="Asia/Shanghai")


def crawl_all_job():
    """定时任务：抓取全部板块"""
    for bid in CRAWLER_MODULES:
        try:
            run_crawler(bid)
            log_crawl(bid, "success", "Scheduled crawl OK")
        except Exception as e:
            log_crawl(bid, "failed", str(e))


def start_scheduler():
    scheduler.add_job(
        crawl_all_job,
        trigger=CronTrigger(minute=0, hour="7-23"),
        id="hourly_crawl",
        name="每小时全量爬虫",
        replace_existing=True,
    )
    scheduler.start()


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
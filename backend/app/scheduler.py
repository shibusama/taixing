"""
APScheduler — 定时爬虫调度
每小时自动全量爬一次，避免在凌晨流量高峰期运行
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.routers.api import run_crawler, CRAWLER_MODULES
from app.database import log_crawl

scheduler = BackgroundScheduler(timezone="Asia/Shanghai")


def crawl_all_job():
    """定时任务：抓取全部7个板块"""
    for bid in CRAWLER_MODULES:
        try:
            run_crawler(bid)
            log_crawl(bid, "success", "Scheduled crawl OK")
        except Exception as e:
            log_crawl(bid, "failed", str(e))


def start_scheduler():
    # 每小时整点抓一次（避开凌晨 2-6 点）
    scheduler.add_job(
        crawl_all_job,
        trigger=CronTrigger(minute=0, hour="7-23"),
        id="hourly_crawl",
        name="每小时爬虫任务",
        replace_existing=True,
    )
    scheduler.start()


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)

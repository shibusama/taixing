"""
数据库模型定义 - 钛星科技新闻站
"""
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, JSON, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from typing import Optional
from datetime import datetime
from coze_coding_dev_sdk.database import Base


class HealthCheck(Base):
    """健康检查表"""
    __tablename__ = "health_check"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ============ 可回收火箭 ============

class RocketCompany(Base):
    """火箭公司"""
    __tablename__ = "rocket_companies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="公司名称")
    country: Mapped[str] = mapped_column(String(50), nullable=False, comment="国家")
    founded_year: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="成立年份")
    logo: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="Logo URL")
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="官网")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="简介")
    valuation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="估值")
    employees: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="员工数")
    achievements: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="成就")
    rockets: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="火箭产品")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("rocket_companies_country_idx", "country"),
    )


class RocketTimeline(Base):
    """火箭时间线"""
    __tablename__ = "rocket_timeline"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_date: Mapped[str] = mapped_column(String(50), nullable=False, comment="事件日期")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="标题")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="描述")
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="公司")
    country: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="国家")
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="状态")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("rocket_timeline_event_date_idx", "event_date"),
    )


# ============ 中美登月 ============

class MoonHighlight(Base):
    """登月亮点"""
    __tablename__ = "moon_highlights"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    num: Mapped[str] = mapped_column(String(10), nullable=False, comment="编号")
    label: Mapped[str] = mapped_column(String(100), nullable=False, comment="标签")
    color: Mapped[str] = mapped_column(String(50), nullable=False, comment="颜色")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, comment="排序")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class MoonComparison(Base):
    """中美登月对比"""
    __tablename__ = "moon_comparison"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aspect: Mapped[str] = mapped_column(String(100), nullable=False, comment="对比维度")
    china_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="中国数据")
    usa_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="美国数据")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


# ============ 中国半导体 ============

class SemiconductorCompany(Base):
    """半导体公司"""
    __tablename__ = "semiconductor_companies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="公司名称")
    category: Mapped[str] = mapped_column(String(100), nullable=False, comment="类别")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="简介")
    products: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="产品")
    progress: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="进展")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("semiconductor_companies_category_idx", "category"),
    )


class SemiconductorTimeline(Base):
    """半导体时间线"""
    __tablename__ = "semiconductor_timeline"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_date: Mapped[str] = mapped_column(String(50), nullable=False, comment="事件日期")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="标题")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="描述")
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="公司")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("semiconductor_timeline_event_date_idx", "event_date"),
    )


# ============ 中国科技AI ============

class ChinaTechCompany(Base):
    """中国科技公司"""
    __tablename__ = "china_tech_companies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="公司名称")
    category: Mapped[str] = mapped_column(String(100), nullable=False, comment="类别")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="简介")
    products: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="产品")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("china_tech_companies_category_idx", "category"),
    )


class ChinaTechTimeline(Base):
    """中国科技时间线"""
    __tablename__ = "china_tech_timeline"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_date: Mapped[str] = mapped_column(String(50), nullable=False, comment="事件日期")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="标题")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="描述")
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="公司")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("china_tech_timeline_event_date_idx", "event_date"),
    )


# ============ 中国大工程 ============

class MegaProject(Base):
    """大工程"""
    __tablename__ = "mega_projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="项目名称")
    category: Mapped[str] = mapped_column(String(100), nullable=False, comment="类别")
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="地点")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="描述")
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="状态")
    investment: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="投资")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("mega_projects_category_idx", "category"),
    )


class MegaProjectTimeline(Base):
    """大工程时间线"""
    __tablename__ = "mega_project_timeline"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_date: Mapped[str] = mapped_column(String(50), nullable=False, comment="事件日期")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="标题")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="描述")
    project: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="项目")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("mega_project_timeline_event_date_idx", "event_date"),
    )


# ============ 可控核聚变 ============

class FusionProject(Base):
    """核聚变项目"""
    __tablename__ = "fusion_projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="项目名称")
    country: Mapped[str] = mapped_column(String(50), nullable=False, comment="国家")
    type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="类型")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="描述")
    status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="状态")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("fusion_projects_country_idx", "country"),
    )


class FusionTimeline(Base):
    """核聚变时间线"""
    __tablename__ = "fusion_timeline"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_date: Mapped[str] = mapped_column(String(50), nullable=False, comment="事件日期")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="标题")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="描述")
    project: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="项目")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("fusion_timeline_event_date_idx", "event_date"),
    )


# ============ 科技资本 ============

class FinanceCompany(Base):
    """科技公司"""
    __tablename__ = "finance_companies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="公司名称")
    category: Mapped[str] = mapped_column(String(100), nullable=False, comment="类别")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="简介")
    valuation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="估值")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("finance_companies_category_idx", "category"),
    )


class FinanceFundingEvent(Base):
    """融资事件"""
    __tablename__ = "finance_funding_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company: Mapped[str] = mapped_column(String(255), nullable=False, comment="公司")
    amount: Mapped[str] = mapped_column(String(100), nullable=False, comment="金额")
    round: Mapped[str] = mapped_column(String(50), nullable=False, comment="轮次")
    date: Mapped[str] = mapped_column(String(50), nullable=False, comment="日期")
    investors: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="投资方")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("finance_funding_events_date_idx", "date"),
    )


class FinanceExchangeRate(Base):
    """汇率"""
    __tablename__ = "finance_exchange_rates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, comment="货币")
    rate: Mapped[str] = mapped_column(String(50), nullable=False, comment="汇率")
    date: Mapped[str] = mapped_column(String(50), nullable=False, comment="日期")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("finance_exchange_rates_date_idx", "date"),
    )


# ============ 爬虫数据 ============

class RawArticle(Base):
    """原始文章"""
    __tablename__ = "raw_articles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    board: Mapped[str] = mapped_column(String(50), nullable=False, comment="版块")
    source: Mapped[str] = mapped_column(String(100), nullable=False, comment="来源")
    title: Mapped[str] = mapped_column(String(500), nullable=False, comment="标题")
    url: Mapped[str] = mapped_column(String(1000), nullable=False, comment="URL")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="内容")
    published_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="发布时间")
    crawled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("raw_articles_board_idx", "board"),
        Index("raw_articles_crawled_at_idx", "crawled_at"),
    )


class CrawlLog(Base):
    """爬虫日志"""
    __tablename__ = "crawl_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    board: Mapped[str] = mapped_column(String(50), nullable=False, comment="版块")
    source: Mapped[str] = mapped_column(String(100), nullable=False, comment="来源")
    status: Mapped[str] = mapped_column(String(20), nullable=False, comment="状态")
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="消息")
    articles_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="文章数")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    __table_args__ = (
        Index("crawl_logs_board_idx", "board"),
        Index("crawl_logs_created_at_idx", "created_at"),
    )


class BoardStatus(Base):
    """版块状态"""
    __tablename__ = "board_status"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    board: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, comment="版块")
    last_crawl_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="最后爬取时间")
    articles_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="文章数")
    sources_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="来源数")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

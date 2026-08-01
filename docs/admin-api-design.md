# 钛星 · 管理后台 API 设计方案（v3 最终版）

> 状态：用户已确认，待 Wave 1 完成后由 Wave 2 代理实现
> 决策：不加管理员登录、不加审计日志；**仅新建 ai_extract_logs 一张后台专用表**；现有业务表结构一律不动、不删数据。

## 一、最简版管理后台功能清单

| 模块 | 功能 | 数据来源 |
|------|------|----------|
| 仪表盘 | 全局统计 + 七大版块状态 + 最近爬取/AI 记录 | 现有表聚合 |
| 文章审核 | 分页、关键字搜索、分类/状态筛选、排序、发布/屏蔽/恢复/删除、批量操作、查看原文 | raw_articles（现有） |
| 最新要闻管理 | 增删改查、上下线（is_active）、排序 | latest_news（现有） |
| 爬虫控制台 | 单版块/全量触发、实时日志、历史日志 | crawl_logs（现有）+ 内存实时日志 |
| AI 提取控制台 | 触发提取、待处理统计、提取历史记录 | ai_extract_logs（新建） |
| 数据同步 | 从 data/*.json 同步指定/全部版块 | 复用 re_sync 函数 |

## 二、新建表（仅 1 张）

**ai_extract_logs — AI 提取历史记录**
现有 ai/stats 只有实时统计，没有历史。后台需要展示"每次提取的时间、范围、结果、状态"。
```
id            bigint PK
category       text          -- 提取分类
limit          int           -- 提取条数
total          int           -- 处理总数
inserted       int           -- 自动入库数
failed         int           -- 失败数
status         text          -- success / failed
message        text          -- 错误信息/摘要
created_at     timestamptz
```

## 三、API 总览

### 现有端点（保留复用）
- GET/POST/PUT/DELETE /api/admin/latest-news[...] — 最新要闻 CRUD
- POST /api/crawl/{board_id}/start、GET /api/crawl/{board_id}/logs、POST /api/crawl — 爬虫
- POST /api/ai/extract、GET /api/ai/stats — AI 提取
- POST /api/admin/articles/{news_id}/status、PUT、DELETE — 文章操作

### 新增端点
| 方法 | 路径 | 用途 |
|------|------|------|
| GET | /api/admin/stats | 仪表盘总览 |
| GET | /api/admin/boards/status | 版块状态面板 |
| GET | /api/admin/crawl-logs?board_id=&limit= | 历史爬虫日志 |
| GET | /api/admin/articles（增强） | 分页 + keyword 搜索 + 筛选 + 排序，返回 {stats, items, total, page, page_size} |
| GET | /api/admin/articles/{news_id} | 单条文章详情 |
| POST | /api/admin/articles/batch-status | 批量审核 |
| GET | /api/admin/ai/logs?limit= | AI 提取历史（新建表） |
| POST | /api/admin/sync[/{board_id}] | JSON → 库同步 |

## 四、不改动的部分
- 现有业务表结构一律不动，不删数据
- 无鉴权（用户已确认不加登录），风险已记录

## 五、实现顺序（功能先行）
1. 前端后台 UI（页面 + JS）按功能模块设计
2. API 端点按模块实现
3. 建 ai_extract_logs 表 + 写入逻辑（AI 提取时记录）
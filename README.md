# 钛星 · 前瞻科技新闻站

> 科技新闻聚合站，支持爬虫自动抓取 + AI 结构化提取 + 管理后台审核。

## 技术栈

- **前端**：纯 HTML + CSS + JS（无框架）
- **后端**：Python 3.12 + FastAPI + Uvicorn
- **数据库**：Supabase（PostgreSQL）
- **Web 服务**：Nginx（反向代理 + 静态文件服务）
- **进程管理**：Supervisor
- **部署**：Docker + docker-compose
- **数据抓取**：requests, curl_cffi, beautifulsoup4
- **AI 提取**：DeepSeek V4 Flash API

## 项目结构

```
/workspace/projects/
├── pages/                  # HTML 页面
│   ├── index.html          # 首页
│   ├── rocket.html         # 可回收火箭
│   ├── moon.html           # 中美登月
│   ├── semiconductor.html  # 中国半导体
│   ├── china-tech.html     # 中国科技AI
│   ├── mega-projects.html  # 中国大工程
│   ├── fusion.html         # 可控核聚变
│   ├── finance.html        # 科技资本
│   └── admin.html          # 管理后台
│
├── css/
│   └── style.css           # 全站样式（科技深色风）
│
├── js/
│   ├── app.js              # 通用交互（Tab切换/菜单/回到顶部/进度条）
│   └── data-loader.js      # 数据加载器（卡片/表格/时间线渲染）
│
├── data/                   # JSON 数据文件（前端 fallback）
│   ├── rocket.json
│   ├── moon.json
│   ├── fusion.json
│   ├── semiconductor.json
│   ├── china-tech.json
│   ├── mega-projects.json
│   └── finance.json
│
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── main.py         # FastAPI 入口
│   │   ├── database.py     # 数据库操作
│   │   ├── ai_extractor.py # AI 新闻提取（DeepSeek V4）
│   │   └── routers/
│   │       └── api.py      # API 路由
│   └── requirements.txt
│
├── crawlers/               # 爬虫模块
│   ├── utils.py            # 公共工具（HTTP/HTML/日期）
│   ├── rocket.py           # 航空航天（SNAPI + Launch Library 2）
│   ├── moon.py             # 中美登月
│   ├── semiconductor.py    # 半导体
│   ├── china_tech.py       # 中国科技AI
│   ├── mega_projects.py    # 中国大工程
│   ├── controlled_fusion.py# 可控核聚变
│   └── finance.py          # 科技资本
│
├── scripts/                # 部署/预览脚本
│   ├── preview_server.py   # 预览服务器
│   ├── coze-preview-build.sh
│   ├── coze-preview-run.sh
│   ├── deploy-build.sh
│   └── deploy-run.sh
│
├── src/storage/database/   # 数据库 schema
│   └── shared/schema.ts
│
├── fetch_data.py           # 爬虫调度入口
├── ai_update.py            # AI 解读脚本（JSON 更新）
├── data_sources.json       # 数据源配置
├── AGENTS.md               # Agent 记忆文件
└── README.md               # 本文件
```

## 数据流程

```
数据源（SNAPI/Launch Library 2/各官网）
        ↓
    爬虫抓取（crawlers/）
        ↓
    raw_articles 表（原始新闻，status=pending）
        ↓
    AI 提取（DeepSeek V4 Flash）
        ↓
    ┌───────┴───────┐
    ↓               ↓
置信度≥0.7      置信度<0.7
    ↓               ↓
自动入库        待人工审核
（rocket_launch_timeline）  （管理后台确认）
        ↓
    前端展示（API → 页面）
```

## 数据库表（25 个）

### 通用表

| 表名 | 行数 | 用途 |
|------|------|------|
| `raw_articles` | 96 | 统一新闻池（所有爬虫数据入库） |
| `board_meta` | 7 | 版块元信息 |
| `board_status` | 7 | 版块状态 |
| `crawl_logs` | 160 | 爬虫执行日志 |
| `health_check` | 1 | 健康检查 |

### 可回收火箭（rocket）

| 表名 | 行数 | 用途 |
|------|------|------|
| `rocket_companies` | 9 | 火箭公司档案 |
| `rocket_launch_timeline` | 10 | 发射时间线（AI 提取） |

### 中美登月（moon）

| 表名 | 行数 | 用途 |
|------|------|------|
| `moon_comparison` | 7 | 中美登月对比 |
| `moon_highlights` | 4 | 登月亮点 |

### 中国半导体（semiconductor）

| 表名 | 行数 | 用途 |
|------|------|------|
| `semiconductor_highlights` | 4 | 半导体亮点 |
| `semiconductor_tab_highlights` | 12 | Tab 亮点 |
| `semiconductor_tab_progress` | 8 | Tab 进展 |
| `semiconductor_technologies` | 0 | 技术列表（空） |
| `semiconductor_timeline` | 0 | 时间线（空） |

### 中国科技AI（china_tech）

| 表名 | 行数 | 用途 |
|------|------|------|
| `china_tech_highlights` | 4 | 科技AI亮点 |
| `china_tech_llm` | 11 | 大模型对比 |
| `china_tech_timeline` | 0 | 时间线（空） |

### 中国大工程（mega_projects）

| 表名 | 行数 | 用途 |
|------|------|------|
| `mega_projects` | 13 | 工程项目列表 |
| `mega_project_highlights` | 4 | 大工程亮点 |
| `mega_project_milestones` | 28 | 里程碑 |

### 可控核聚变（fusion）

| 表名 | 行数 | 用途 |
|------|------|------|
| `fusion_highlights` | 4 | 核聚变亮点 |
| `fusion_timeline` | 18 | 核聚变时间线 |

### 科技资本（finance）

| 表名 | 行数 | 用途 |
|------|------|------|
| `finance_sections` | 10 | 资本版块 |
| `finance_highlights` | 16 | 资本亮点 |
| `finance_grids` | 76 | 资本数据网格 |

### raw_articles 字段

| 字段 | 说明 |
|------|------|
| news_id | 主键（URL 哈希） |
| source_name | 来源媒体 |
| source_url | 原文链接（去重依据） |
| title | 标题 |
| summary | 摘要 |
| raw_content | 原始正文 |
| cover_image | 封面图 |
| tags | AI 标签（JSON） |
| category | 分类（航空航天/半导体/...） |
| hot_score | 热度分值 |
| sentiment | 情感倾向 |
| status | pending/online/block |

## 爬虫数据源

| 板块 | 数据源 | 方式 |
|------|--------|------|
| 航空航天 | SNAPI（Spaceflight News API） | API，聚合 20+ 权威媒体 |
| 航空航天 | Launch Library 2 | API，全球发射日历 |
| 中美登月 | NASA/CNSA 等 | HTML 爬取 |
| 半导体 | 各半导体媒体 | HTML 爬取 |
| 中国科技AI | 科技媒体 | HTML 爬取 |
| 中国大工程 | 基建新闻 | HTML 爬取 |
| 可控核聚变 | 核聚变新闻 | HTML 爬取 |
| 科技资本 | 金融数据 | HTML 爬取 |

## 管理后台

访问 `/admin.html` 进入管理后台：

- **爬虫控制台**：触发爬虫，查看实时日志
- **AI 提取控制台**：触发 AI 处理，查看提取结果
- **文章列表**：筛选/排序/发布/屏蔽
- **统计信息**：待处理/已入库数量

## API 端点

| 端点 | 说明 |
|------|------|
| `GET /api/boards/{board_id}/full` | 获取版块完整数据 |
| `GET /api/rocket-timeline` | 获取火箭发射时间线 |
| `GET /api/admin/articles` | 获取原始文章列表 |
| `POST /api/admin/articles/{id}/publish` | 发布文章 |
| `POST /api/crawl/{board_id}/start` | 触发爬虫 |
| `GET /api/crawl/{board_id}/logs` | 获取爬虫日志 |
| `POST /api/ai/extract` | 触发 AI 提取 |
| `GET /api/ai/stats` | 获取 AI 统计 |

## 运行命令

```bash
# 全量抓取
python fetch_data.py

# 只抓某个板块
python fetch_data.py --rocket
python fetch_data.py --fusion

# AI 解读（JSON 更新）
python ai_update.py --dry-run  # 预览
python ai_update.py            # 正式写入
```

## 部署

- **部署平台**：Coze Deploy
- **预览端口**：5000
- **生产架构**：Nginx + FastAPI + Supervisor（Docker 容器内）

## 技术特点

- **数据库驱动**：数据从 JSON 迁移到 PostgreSQL，支持 AI 提取和管理后台
- **统一新闻池**：所有爬虫数据统一写入 raw_articles，按 category 分类处理
- **AI 结构化**：DeepSeek V4 自动提取发射任务信息，置信度过滤
- **管理后台**：可视化触发爬虫、AI 提取、文章审核
- **深色科技风**：深蓝背景 + 青/橙/紫霓虹点缀 + 星空背景
- **移动端适配**：480px/768px/1024px 三断点响应式

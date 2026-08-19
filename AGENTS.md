# AGENTS.md - 钛星 · 前瞻科技新闻站

> 本文档面向 AI 编程助手，所有代码修改、脚本调试、部署操作必须严格遵守下文约束。

 ## 🎯 沟通风格
 
 1. **只回答用户提出的问题**，不主动提出修复、优化方案
 2. **用户明确要求修复/调整代码，再执行修改**；无指令仅做现象解释
 3. **回答简洁直接**，避免冗余赘述，不要重复解释
 
 ## 📋 操作流程
 
 1. **先回答后执行**：用户提问时，先回答问题，不要直接跑去执行代码或命令。等用户确认需要执行时再执行
 2. **只做明确要求的事**：不要自作主张去测试、爬虫、重启服务等
 3. **修改前征得同意**：修改代码前，先告诉用户修改思路，等用户同意后再动手改。文案类改动（标题、标签、布局文本）经确认后可执行

## 项目概述

钛星（taixing）科技新闻聚合网站，数据与页面分离，依靠 Python 爬虫自动抓取 + DeepSeek AI 提取结构化数据。

**七大版块**：可回收火箭、中美登月、中国科技AI（含半导体Tab）、超级工程、可控核聚变、科技资本、宏观指标监控。

## 技术栈

- **前端**：原生 HTML + CSS + JS + JSON（无前端框架）
- **后端**：Python 3.12 + FastAPI + Uvicorn
- **数据库**：Supabase（PostgreSQL）
- **Web 服务**：Nginx（静态文件 + API 反向代理）
- **进程管理**：Supervisor
- **容器部署**：Docker + docker-compose
- **数据抓取**：requests, curl_cffi, beautifulsoup4
- **AI 处理**：DeepSeek V4 Flash API

## 目录结构

```
/workspace/projects/
├── pages/                  # HTML 页面（已整理到统一目录）
│   ├── index.html          # 首页
│   ├── rocket.html         # 可回收火箭
│   ├── moon.html           # 中美登月
│   ├── china-tech.html     # 中国科技AI（含半导体Tab，半导体板块已并入）
│   ├── mega-projects.html  # 中国超级工程
│   ├── fusion.html         # 可控核聚变
│   ├── finance.html        # 科技资本
│   ├── macro.html           # 宏观指标监控
│   ├── admin.html          # 管理后台
│   └── _archived/          # 已下线页面（如 semiconductor.html）
├── css/style.css           # 全站样式
├── js/
│   ├── app.js              # 通用页面交互
│   └── data-loader.js      # 数据渲染
├── data/                   # JSON 数据层
│   └── *.json              # 各版块业务数据
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── main.py         # FastAPI 入口
│   │   ├── database.py     # 数据库操作
│   │   ├── ai_extractor.py # AI 新闻提取（DeepSeek）
│   │   └── routers/api.py  # API 路由
│   └── requirements.txt
├── crawlers/               # 爬虫模块
│   ├── utils.py            # 公共工具
│   ├── rocket.py           # 航空航天（SNAPI + Launch Library 2）
│   ├── moon.py             # 中美登月
│   ├── semiconductor.py    # 半导体
│   ├── china_tech.py       # 中国科技AI
│   ├── mega_projects.py    # 超级工程
│   ├── controlled_fusion.py # 可控核聚变
│   └── finance.py          # 科技资本
├── scripts/                # 部署/预览脚本
├── fetch_data.py           # 爬虫入口
├── ai_update.py            # AI 解读脚本
├── data_sources.json       # 数据源配置
└── .coze                   # Coze 平台配置
```

## 核心入口

| 入口 | 文件 |
|------|------|
| 前端页面 | `pages/index.html` |
| 后端 API | `backend/app/main.py` |
| 爬虫入口 | `fetch_data.py` |
| AI 提取 | `backend/app/ai_extractor.py` |
| 管理后台 | `pages/admin.html` |

## 常用命令

```bash
# 爬虫
python3 fetch_data.py                    # 爬取所有版块
python3 fetch_data.py --rocket           # 只爬可回收火箭
python3 fetch_data.py --dry-run          # 预览模式（不写入）

# AI 提取
curl -X POST "http://localhost:5000/api/ai/extract?category=rocket&limit=10"

# 预览服务器
python3 scripts/preview_server.py        # 启动预览（端口 5000）

# 数据库查询
# 使用 exec_sql 工具，env=develop 或 env=product
```

## 数据流程

```
爬虫（SNAPI/LL2/各官网）
    ↓
raw_articles（统一新闻池，status=pending）
    ↓
AI 提取（DeepSeek V4 Flash）
    ↓
├── 置信度 ≥ 0.7 → 自动写入 rocket_launch_timeline
└── 置信度 < 0.7 → 待人工审核（status=pending 保留）
    ↓
前端展示（从 API 读取）
```

## 数据库表（25 个）

### 通用表（5 个）
- `raw_articles` - 统一新闻池
- `board_meta` - 版块元信息
- `board_status` - 版块状态
- `crawl_logs` - 爬虫执行日志
- `health_check` - 健康检查

### 可回收火箭（2 个）
- `rocket_companies` - 火箭公司档案
- `rocket_launch_timeline` - 发射时间线（AI 提取）

### 中美登月（2 个）
- `moon_comparison` - 中美登月对比
- `moon_highlights` - 登月亮点

### 中国半导体（5 个）— 已并入中国科技（china-tech full API 聚合输出）
- `semiconductor_highlights` - 亮点
- `semiconductor_tab_highlights` - Tab 亮点
- `semiconductor_tab_progress` - Tab 进展
- `semiconductor_technologies` - 技术列表
- `semiconductor_timeline` - 时间线

### 中国科技AI（3 个）
- `china_tech_highlights` - 亮点
- `china_tech_llm` - 大模型对比
- `china_tech_timeline` - 时间线

### 中国超级工程（3 个）
- `mega_projects` - 工程项目
- `mega_project_highlights` - 亮点
- `mega_project_milestones` - 里程碑

### 可控核聚变（2 个）
- `fusion_highlights` - 亮点
- `fusion_timeline` - 时间线

### 科技资本（3 个）
- `finance_sections` - 版块
- `finance_highlights` - 亮点
- `finance_grids` - 数据网格

## 运行模式

| 模式 | 端口 | 架构 |
|------|------|------|
| 预览（Coze Dev） | 5000 | preview_server.py（FastAPI 静态文件 + API） |
| 生产（Coze Deploy） | 5000 | Nginx + FastAPI + Supervisor |

## 🚫 硬性规范 / 禁止事项

1. **禁止将数据内容硬编码到 HTML 页面**：数据更新只能修改 data/*.json 或数据库。文案修改（标题、标签、布局文本）经确认后可执行
2. **禁止修改数据库表结构**：除非用户明确要求
3. **禁止删除数据**：除非用户明确要求
4. **AI 更新安全**：只允许 value 变化，key/结构变化直接拒绝写入
5. **写入前自动备份**：JSON 更新前备份到 `data/_backups/`
6. **API 限流处理**：LL2/SNAPI 遇到 429 时，添加延迟重试，不要频繁请求
7. **Python 版本**：运行时使用 Python 3.12（不可用时允许 >= 3.10 的兼容版本）

## 🔧 故障排查

### API 限流（429 Too Many Requests）
- **原因**：请求太频繁，触发 LL2/SNAPI 速率限制
- **解决**：添加 `time.sleep()` 延迟，每次请求间隔 2-5 秒

### DeepSeek API 报错
- **检查**：API Key 是否配置（`DEEPSEEK_API_KEY` 环境变量）
- **检查**：模型名称是否正确（`deepseek-v4-flash`）

### 预览端口占用
- **检查**：`ss -tlnp | grep 5000`
- **解决**：`pkill -f preview_server.py` 后重启

### 数据库连接失败
- **检查**：Supabase 环境变量是否配置
- **检查**：网络是否可达

## Coze 配置

- **project_type**：web
- **preview_enable**：enabled
- **runtime**：python-3.12
- **预览脚本**：`scripts/coze-preview-build.sh` + `scripts/coze-preview-run.sh`
- **部署脚本**：`scripts/deploy-build.sh` + `scripts/deploy-run.sh`

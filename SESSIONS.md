# SESSIONS.md - 钛星多会话分配方案

> 本文档定义钛星项目在扣子编程中的多会话分工。每个会话的 AI 助手只做自己模块的事，不越界修改其他模块代码。

---

## 会话总览

| 会话 | 专注方向 | 覆盖文件 |
|------|---------|---------|
| ① 前端 & 样式 | 页面布局、样式、交互、响应式 | `pages/`、`css/`、`js/` |
| ② 后端 & API | API 路由、数据库、AI 提取 | `backend/`、数据库（Supabase） |
| ③ 爬虫 & 数据 | 数据抓取、AI 解读、数据清洗 | `crawlers/`、`fetch_data.py`、`ai_update.py` |
| ④ 部署 & 运维 | 部署配置、日志排查、服务监控 | `scripts/`、Docker、Nginx、Supervisor |

---

## 会话① - 前端 & 样式

**专注范围：**
- `pages/*.html` — 9 个页面（首页、火箭、登月、半导体、科技AI、大工程、核聚变、资本、管理后台）
- `css/style.css` — 全站样式
- `js/app.js` — 通用交互（Tab切换、菜单、回到顶部、进度条）
- `js/data-loader.js` — 数据渲染（卡片、表格、时间线）

**职责：**
- 改页面布局和排版
- 调样式、配色、动效
- 加交互效果、组件
- 做响应式适配（480px / 768px / 1024px）
- 修前端 bug

**禁止：**
- ❌ 修改后端代码
- ❌ 修改数据库
- ❌ 修改爬虫逻辑
- ❌ 修改部署配置

---

## 会话② - 后端 & API

**专注范围：**
- `backend/app/main.py` — FastAPI 入口
- `backend/app/database.py` — 数据库操作
- `backend/app/ai_extractor.py` — AI 新闻提取（DeepSeek）
- `backend/app/routers/api.py` — API 路由
- `backend/requirements.txt` — 依赖
- Supabase 数据库所有表

**职责：**
- 写、改 API 端点
- 改数据库表结构（需用户明确同意）
- 调 Supabase 查询逻辑
- 修 AI 提取 prompt 和逻辑
- 调后端性能

**禁止：**
- ❌ 修改前端 HTML/CSS/JS
- ❌ 修改爬虫脚本
- ❌ 修改部署配置

---

## 会话③ - 爬虫 & 数据

**专注范围：**
- `crawlers/*.py` — 7 个版块爬虫
- `crawlers/utils.py` — 爬虫公共工具
- `fetch_data.py` — 爬虫调度入口
- `ai_update.py` — AI 解读（JSON 更新）
- `data/*.json` — JSON 数据文件
- `data_sources.json` — 数据源配置

**职责：**
- 加新数据源
- 调爬虫解析逻辑
- 改 AI 提取 prompt
- 数据清洗、去重
- 处理爬虫报错（429 限流等）

**禁止：**
- ❌ 修改前端页面
- ❌ 修改后端 API
- ❌ 修改部署配置

---

## 会话④ - 部署 & 运维

**专注范围：**
- `scripts/` — 预览/部署脚本
- `.coze` — Coze 平台配置
- `docker-compose.yml`（如有）
- Nginx 配置
- Supervisor 配置
- 运行日志（`crawl_logs` 表、服务日志）

**职责：**
- 调部署脚本
- 看日志排错
- 监控服务是否正常
- 处理端口占用、服务重启
- 配置环境变量

**禁止：**
- ❌ 修改前端代码
- ❌ 修改后端逻辑
- ❌ 修改爬虫逻辑
- ❌ 修改数据库表结构

---

## 跨会话协作规则

1. **各会话独立上下文** — 每个 AI 不知道其他会话的存在和对话内容
2. **发现问题告知主人** — 如果发现其他模块有问题，直接告诉主人，不要跨模块动手改
3. **修改前先征得同意** — 所有代码修改必须先告诉主人思路，等同意再动手
4. **整体项目信息** — 需要了解项目全貌时，先读 `README.md` 和 `AGENTS.md`

---



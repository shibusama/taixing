# AGENTS.md - 钛星 · 前瞻科技新闻站

## 项目概述

钛星（taixing）是一个纯静态科技新闻网站，数据与页面分离，支持脚本自动抓取 + AI 解读更新。包含可回收火箭、中美登月、半导体、中国科技AI、大工程、可控核聚变、科技资本七大版块。

## 技术栈

- **前端**：纯 HTML + CSS + JS + JSON（无框架）
- **后端**：Python 3.13 + FastAPI + Uvicorn
- **Web 服务**：Nginx（反向代理 + 静态文件服务）
- **进程管理**：Supervisor（管理 Nginx + FastAPI）
- **部署**：Docker + docker-compose
- **数据抓取**：requests, curl_cffi, beautifulsoup4
- **AI 解读**：DeepSeek API

## 目录结构

```
/workspace/projects/
├── index.html              # 首页：Hero + 六大版块入口卡片 + 最新要闻
├── rocket.html             # 可回收火箭
├── moon.html               # 中美登月
├── semiconductor.html      # 中国半导体
├── china-tech.html         # 中国科技AI
├── mega-projects.html      # 中国大工程
├── fusion.html             # 可控核聚变
├── finance.html            # 科技资本
├── css/style.css           # 全站样式（科技深色风）
├── js/
│   ├── app.js              # 通用交互（Tab切换/菜单/回到顶部/进度条）
│   └── data-loader.js      # JSON 数据加载器（卡片/表格/时间线渲染）
├── data/                   # 数据层（脚本只改这里，不动 HTML）
│   ├── *.json              # 各版块数据文件
│   ├── _snapshots/         # 爬虫原始快照
│   └── _reports/           # 爬取执行报告
├── backend/                # FastAPI 后端
│   ├── app/main.py         # FastAPI 入口
│   ├── app/database.py     # 数据库逻辑
│   ├── app/llm.py          # LLM 调用
│   ├── app/routers/        # API 路由
│   ├── app/scheduler.py    # 定时任务
│   └── requirements.txt    # Python 依赖
├── fetch_data.py           # 数据抓取脚本（13个源头）
├── ai_update.py            # AI自动解读脚本（DeepSeek API）
├── nginx.conf              # Nginx 配置（监听 8080）
├── supervisord.conf        # Supervisor 配置
├── Dockerfile              # Docker 构建文件
├── docker-compose.yml      # Docker Compose 编排
└── setup.sh                # 一键部署脚本
```

## 关键入口 / 核心模块

- **前端入口**：`index.html`（首页），各版块独立 HTML 页面
- **后端入口**：`backend/app/main.py`（FastAPI 应用）
- **数据抓取**：`fetch_data.py`（13 个数据源）
- **AI 解读**：`ai_update.py`（DeepSeek API 驱动）
- **样式**：`css/style.css`（深色科技风，892 行）
- **数据加载**：`js/data-loader.js`（JSON → DOM 渲染）

## 运行与预览

- **生产模式**：Docker 容器内 Supervisor 管理 Nginx(8080) + FastAPI(8000)
- **预览模式**：通过 `scripts/coze-preview-build.sh` 和 `scripts/coze-preview-run.sh` 启动
- **部署模式**：通过 `scripts/deploy-build.sh` 和 `scripts/deploy-run.sh` 启动（Coze Deploy）
- **端口**：预览和部署使用 5000 端口，生产使用 8080 端口
- **预览服务器**：`scripts/preview_server.py` 使用 Python FastAPI 同时服务静态文件和 API，替代 Nginx
- **部署架构**：Coze Deploy 使用 Nginx + FastAPI + Supervisor 三件套（Docker 级别）
  - Nginx：监听 5000 端口，静态文件服务 + API 反向代理
  - FastAPI/Uvicorn：监听 8000 端口，后端 API
  - Supervisor：管理 Nginx 和 FastAPI 进程
- **Nginx 配置**：静态文件直接服务（带缓存策略），`/api/` 反向代理到 FastAPI

## Coze 配置说明

- **根 .coze**：位于 `/workspace/projects/.coze`，技术项目与工作区根目录重合（path = "."）
- **project_type**：web（前端静态页面 + 后端 FastAPI API）
- **preview_enable**：enabled
- **预览链路**：`[dev].build` → `scripts/coze-preview-build.sh`（安装依赖），`[dev].run` → `scripts/coze-preview-run.sh`（启动预览服务器）
- **部署链路**：`[deploy].build` → `scripts/deploy-build.sh`（安装依赖），`[deploy].run` → `scripts/deploy-run.sh`（启动服务，监听 5000 端口）
- **部署 profile**：kind = "service", flavor = "web"
- **运行时**：python-3.12

## 用户偏好与长期约束

- 数据层与展示层分离：脚本只改 `data/*.json`，不动 HTML
- AI 更新安全机制：只允许 value 变化，key/结构变化直接拒绝写入
- 写入前自动备份到 `data/_backups/`
- 支持 `--dry-run` 模式预览变更
- Python 依赖使用清华镜像源加速
- Docker 使用阿里云镜像源加速

## 常见问题和预防

- **NASA 官网**：经常超时，需做好容错
- **汇率数据**：来自 Frankfurter API（ECB 数据），直接写入 `finance.json`
- **AI 解读**：DeepSeek API 调用，需配置 `DEEPSEEK_API_KEY` 环境变量
- **API 调用必须用正确的 Accept 头**：调用 JSON API 时必须用 `fetch_json_api()`（Accept: application/json），不能用 `fetch_json()`（Accept: text/html）。否则 API 会返回 HTML 而不是 JSON，导致解析失败。教训：Launch Library 2 API 因 Accept 头错误导致爬虫失败。

## 用户交互原则

- **只回答用户问的问题**：用户问什么就答什么，不要主动建议修复方案
- **用户说修才修**：除非用户明确要求修复，否则只解释原因，不主动提出"要修吗？"
- **简洁直接**：回答问题要简洁，不要啰嗦，不要重复解释

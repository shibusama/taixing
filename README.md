# 钛星 · 前瞻科技新闻站

> 纯静态科技新闻网站，数据与页面分离，支持脚本自动抓取 + AI 解读更新。

## 项目结构

```
rocket-news/
├── index.html              # 首页：Hero + 六大版块入口卡片 + 最新要闻
├── rocket.html             # 可回收火箭（Tab：全球进展 / 技术对比 / 发射计划）
├── moon.html               # 中美登月（嫦娥七号 / Artemis / 南极水冰）
├── semiconductor.html      # 中国半导体（芯片制造 / EDA / 光刻机 / 国产替代）
├── china-tech.html         # 中国科技AI（大模型对比表 / 量子 / 新能源 / 超算）
├── mega-projects.html      # 中国大工程（川藏铁路 / 中吉乌 / 平陆运河 / 特高压）
├── fusion.html             # 可控核聚变（EAST / ITER / CFS / 三列平行时间线）
├── finance.html            # 科技资本（美联储利率 / 汇率 / SpaceX / AI巨头估值）
│
├── css/
│   └── style.css           # 全站样式（科技深色风，892行）
│
├── js/
│   ├── app.js              # 通用交互（Tab切换 / 移动端汉堡菜单 / 回到顶部 / 阅读进度条）
│   └── data-loader.js      # JSON 数据加载器（卡片渲染 / 表格渲染 / 时间线渲染）
│
├── data/                   # 数据层（脚本只改这里，不动 HTML）
│   ├── rocket.json         # 可回收火箭数据
│   ├── moon.json           # 登月计划数据
│   ├── fusion.json         # 核聚变数据
│   ├── semiconductor.json  # 半导体数据
│   ├── china-tech.json     # 中国科技AI数据（含大模型对比表）
│   ├── mega-projects.json  # 大工程数据
│   ├── finance.json        # 科技资本数据（含汇率/美联储）
│   ├── _snapshots/         # 爬虫抓取的原始网页快照（调试用）
│   └── _reports/           # 每次爬取的执行报告
│
├── fetch_data.py           # 数据抓取脚本（1199行，13个源头）
├── ai_update.py            # AI自动解读脚本（481行，调DeepSeek API）
├── .env.example            # API Key 配置模板（实际key已硬编码在ai_update.py中）
├── .gitignore              # Git忽略规则
└── README.md               # 本文件
```

## 页面说明

| 页面 | 内容 | 数据文件 |
|------|------|----------|
| `index.html` | 首页，六大版块入口卡片 + 最新要闻聚合 | 无（静态） |
| `rocket.html` | 可回收火箭：9家公司进展 / 9款火箭参数对比 / 发射计划时间线 | `rocket.json` |
| `moon.html` | 中美登月竞赛：嫦娥七号 / 长征十号 / 梦舟 vs Artemis II/III/IV | `moon.json` |
| `semiconductor.html` | 中国半导体：芯片制造 / EDA / 光刻机 / 国产替代 | `semiconductor.json` |
| `china-tech.html` | 中国科技AI：大模型对比表 / 量子计算 / 新能源 / 超算 | `china-tech.json` |
| `mega-projects.html` | 中国大工程：川藏铁路 / 中吉乌 / 平陆运河 / 特高压 | `mega-projects.json` |
| `fusion.html` | 可控核聚变：EAST / ITER / CFS / 全球三列平行时间线 | `fusion.json` |
| `finance.html` | 科技资本：美联储利率 / 汇率市场 / SpaceX / AI巨头估值 | `finance.json` |

## 脚本说明

### fetch_data.py — 数据抓取

从 13 个一手源头抓取最新数据：

| 源头 | 板块 | 方式 |
|------|------|------|
| SpaceX 官网 | 火箭 | requests |
| Blue Origin 官网 | 火箭 | requests |
| Rocket Lab 官网 | 火箭 | requests |
| ITER 官网 | 核聚变 | requests |
| CFS 官网 | 核聚变 | requests |
| ASIPP（中科院等离子体所） | 核聚变 | requests |
| Anthropic 官网 | 科技资本 | requests |
| DeepSeek 官网 | 中国科技 | requests |
| Moonshot 官网 | 中国科技 | requests |
| 中芯国际官网 | 半导体 | curl_cffi（绕Apache TLS指纹） |
| Frankfurter API（ECB数据） | 汇率 | requests → 直接写入 finance.json |
| Launch Library 2 API | 发射日历 | requests |
| NASA 官网 | 登月 | requests（常超时） |

```bash
# 全量抓取
python fetch_data.py

# 只抓某个板块
python fetch_data.py --rocket
python fetch_data.py --fusion
python fetch_data.py --semicon
python fetch_data.py --finance
python fetch_data.py --ai

# 抓取结果：
#   - 汇率直接写入 finance.json
#   - 其他数据存入 data/_snapshots/ 和 data/_reports/
```

### ai_update.py — AI自动解读

调用 DeepSeek API 读取快照数据，自动更新 7 个 JSON 文件：

```bash
# 先看变更（不写入）
python ai_update.py --dry-run

# 指定板块
python ai_update.py rocket --dry-run
python ai_update.py finance --dry-run

# 确认无误后正式写入
python ai_update.py

# 写入后自动备份到 data/_backups/
```

**安全机制：**
- 只允许 value 变化，key/结构变化直接拒绝写入
- 写入前自动备份到 `data/_backups/`
- 支持 `--dry-run` 只看不写

## 完整更新流程

```bash
# 1. 抓取数据
python fetch_data.py

# 2. AI解读（先看变更）
python ai_update.py --dry-run

# 3. 确认后正式写入
python ai_update.py

# 4. 推送到 GitHub
git add -A
git commit -m "update: 数据刷新"
git push

# 5. Coze 自动从 GitHub 拉取部署
```

## 部署方式

- **GitHub 仓库**：https://github.com/shibusama/taixing
- **部署平台**：Coze（从 GitHub 拉取，无需域名备案）
- **技术栈**：纯静态 HTML + CSS + JS + JSON，无后端

## 技术特点

- **数据层分离**：所有动态数据在 `data/*.json`，HTML 通过 JS fetch 渲染
- **一键更新**：`fetch_data.py` 抓取 → `ai_update.py` 解读 → `git push` 部署
- **反爬处理**：curl_cffi 伪装 Chrome TLS 指纹绕过 Apache 403
- **AI 解读**：DeepSeek API 自动分析快照数据，结构校验确保安全
- **深色科技风**：深蓝背景 + 青/橙/紫霓虹点缀 + 星空背景
- **移动端适配**：480px/768px/1024px 三断点响应式

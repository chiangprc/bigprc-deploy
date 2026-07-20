# BigPRC 开发者手册

> **站点**: https://www.bigprc.com
> **仓库**: https://github.com/chiangprc/bigprc-deploy
> **最后更新**: 2026-07-20 (P0-B + P1 数据层升级完成，AI 流水线全链路闭环)

---

> 🔴 **日常操作看这里 → [WORKFLOW_DAILY.md](WORKFLOW_DAILY.md)**
> 🟢 **v2.0 升级报告 → [docs/V2_UPGRADE_COMPLETED.md](docs/V2_UPGRADE_COMPLETED.md)**
> 本文档是完整的系统架构和配置参考。日常改页面、更新资源、部署上线等操作，请优先查阅《开发者日常工作流》。

---

## 目录

1. [项目概述](#1-项目概述)
2. [设计系统](#2-设计系统)
3. [系统架构](#3-系统架构)
4. [目录结构](#4-目录结构)
5. [VPS 运行时拓扑](#5-vps-运行时拓扑)
6. [环境搭建（一次性）](#6-环境搭建一次性)
7. [日常开发流程](#7-日常开发流程)
8. [脚本参考](#8-脚本参考)
9. [Nginx 配置说明](#9-nginx-配置说明)
10. [运维自动化](#10-运维自动化)
11. [部署流程](#11-部署流程)
12. [模板系统](#12-模板系统)
13. [环境变量参考](#13-环境变量参考)
14. [Git 管理策略](#14-git-管理策略)
15. [VPS ↔ 本地同步指南](#15-vps--本地同步指南)
16. [常见问题排查](#16-常见问题排查)

---

## 1. 项目概述

BigPRC 是一个**极客资源聚合分享站**——从 Excel 数据源读取资源列表，通过 Python 脚本自动生成全站静态 HTML，部署到 Ubuntu VPS + Nginx 对外服务。全站约 1,260+ 条资源，覆盖软件工具、学习资料、影音娱乐等领域。

### 核心技术栈

| 层 | 技术 | 用途 |
|---|------|------|
| 数据层 | Excel (.xlsx) → SQLite | 资源数据存储与清洗 |
| 生成层 | Python 3.12 + Jinja2 | 静态 HTML 页面批量渲染 |
| AI 辅助 | OpenAI 兼容 API (DeepSeek) | 自动生成 SEO 描述文案 |
| 服务器 | Ubuntu 24.04 + Nginx | 静态站点托管 + 反向代理 |
| 网关 | OpenClaw (Node.js) | 管理控制台 WebSocket 代理 |
| 控制面板 | 1Panel + Sui | 服务器管理面板 |
| 容器 | Docker | 运行 OpenClaw、new-api、数据库等服务 |
| 版本控制 | Git + GitHub | 配置与脚本的版本管理 |
| 部署 | Bash deploy.sh | 软链接 + Nginx 热重载 |

### 页面 URL 路由规则

| URL 模式 | 对应内容 | 实现方式 |
|----------|---------|---------|
| `/` | 首页 (index.html) | 静态文件 (来自 custom-pages) |
| `/list.html` | 资源列表页 | Jinja2 生成 + fetch /index.json |
| `/go/{res_id}` | 资源详情页（如 `/go/p001`） | Nginx rewrite → `/static/page/p001.html` |
| `/jump/{res_id}` | 普通链接中转跳转 | Nginx include jump_rules.conf → 302 |
| `/jump/{res_id}_short` | 短链中转跳转 | 同上 |
| `/ws` | WebSocket | 反向代理到 OpenClaw :18789 |
| `/tools/claudeek.html` | Claudeek 产品页 | 手工静态页面 |
| `/opensearch.xml` | 浏览器地址栏搜索 | 静态 XML |
| `/sitemap.xml` | 搜索引擎地图 | auto_generate.py 生成 |
| `/404.html` | 自定义 404 | 手工静态页面 |

### 线上域名体系

```
bigprc.com         ─── 裸域，301 → www + OpenClaw 反向代理 (:18789)
www.bigprc.com     ─── 主站（静态资源展示 + /ws WebSocket）
claw.bigprc.com    ─── OpenClaw 管理控制台 (:18789)
api.bigprc.com     ─── 授权引擎 API (:8088) + /api/kick (:9000)
```

---

## 2. 设计系统

全站遵循 **Swiss 国际主义扁平风格**。完整规范见 [docs/DESIGN_SPEC_FLAT_REDESIGN.md](docs/DESIGN_SPEC_FLAT_REDESIGN.md)。

**设计令牌**：
| 属性 | 亮色 | 暗色 |
|------|------|------|
| 背景 | `#ffffff` | `#121212` |
| 前景文字 | `#1a1a1a` | `#e0e0e0` |
| 次级文字 | `#666666` | `#999999` |
| 边框 | `#e5e5e5` | `#2a2a2a` |
| 主色（链接）| `#1a365d` | `#5c9ce6` |
| 强调 CTA | `#c0392b` | `#e74c3c` |
| 卡片底色 | `#fafafa` | `#1a1a1a` |

**核心原则**：无图标、无渐变、无阴影（卡片悬浮除外）、1px 边框、4px 圆角、system-ui 字体。暗色模式通过 `<head>` 内联脚本在 DOM 渲染前设置 `[data-theme="dark"]` 属性，杜绝白屏闪烁。

---

## 3. 系统架构

### 整体数据流

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Excel 表格  │ ──▶ │  SQLite 数据库 │ ──▶ │  Jinja2 模板  │ ──▶ │  静态 HTML   │
│  (数据源)    │     │  (中间层)     │     │  (渲染引擎)   │     │  (最终产物)  │
└─────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
      │                                                             │
      │  pantools_sync.py               auto_generate.py            │
      │                                                             ▼
┌──────────────┐                                            ┌──────────────┐
│  AI SEO 引擎  │ ───────────────────────────────────────▶  │    Nginx     │
│  (DeepSeek)   │          ai_seo_writer.py                 │  Web Server  │
└──────────────┘                                            └──────┬───────┘
                                                                   │
                                                             ┌─────▼──────┐
                                                             │  用户浏览器  │
                                                             └────────────┘
```

### 开发→部署流水线

```
本地 Windows                        GitHub                          VPS 服务器
─────────────                      ────────                         ──────────
1. 编辑 Excel
2. pantools_sync.py  ─┐
3. auto_generate.py   ├─▶ git push ──▶ github.com/             ──▶ git pull
4. preview.ps1 预览   ─┘               chiangprc/bigprc-deploy      bash deploy.sh
                                                                   (软链接 + 热重载)
```

---

## 4. 目录结构

> **注意**: 本地 repo 是 VPS 文件系统的**镜像备份**，不是直接部署的源码仓库。
> VPS 上通过 `/root/bigprc-deploy/` 的 git clone 管理，关键路径通过软链接映射到系统目录。

```
bigprc configs/                       ← 项目根目录 (本地: E:\Claudeek\Projects\bigprc configs)
│                                     ← VPS: /root/bigprc-deploy/
├── README.md                         ← 项目索引
├── DEVELOPER_MANUAL.md               ← 本文档（开发者手册）
├── WORKFLOW_DAILY.md                 ← 日常运维速查
├── vps_audit.sh                      ← VPS 结构审计脚本
│
├── deploy.sh                         ← VPS 一键部署（软链接 + Nginx 热重载）
├── setup.sh / setup.ps1              ← 本地环境初始化（一次性）
├── preview.sh / preview.ps1          ← 本地预览服务器启动脚本
├── local_server.py                   ← 本地 HTTP 服务器（模拟 Nginx rewrite）
├── .gitignore                        ← 推送排除清单
│
├── docs/                             ← 项目文档
│   ├── DESIGN_SPEC_FLAT_REDESIGN.md  ← 设计规范
│   ├── EVALUATION_AND_IMPROVEMENT_PLAN.md
│   └── PROJECT_STRUCTURE.md          ← 项目结构手册
│
├── etc/                              ← 服务器配置 (VPS 路径: /etc/)
│   └── nginx/
│       ├── nginx.conf                ← Nginx 主配置（含 rate limit zones）
│       ├── fastcgi.conf / fastcgi_params / mime.types
│       ├── proxy_params / scgi_params / uwsgi_params
│       ├── koi-utf / koi-win / win-utf
│       ├── sites-available/          ← 站点配置源文件
│       │   ├── default               ← www.bigprc.com 主站
│       │   ├── openclaw              ← bigprc.com 裸域 + 控制台代理
│       │   ├── claw                  ← claw.bigprc.com 控制台
│       │   └── api.bigprc.com        ← api.bigprc.com 授权引擎 (2026-07 新增)
│       ├── sites-enabled/            ← 启用的站点 (VPS 上为 symlink)
│       │   ├── default → .../sites-available/default
│       │   ├── openclaw → .../sites-available/openclaw
│       │   ├── claw → .../sites-available/claw
│       │   └── api.bigprc.com → /etc/nginx/sites-available/api.bigprc.com
│       └── snippets/
│           ├── security_headers.conf ← CSP 安全策略头
│           ├── fastcgi-php.conf
│           ├── snakeoil.conf
│           └── jump_rules.conf      ← 自动生成 (⚠️ gitignore, VPS 上由 auto_generate.py 管理)
│
├── root/                             ← VPS /root 目录内容
│   ├── bashrc                        ← VPS shell 配置 (⚠️ gitignore, 含 7 个 API Key)
│   ├── openclaw.log                  ← OpenClaw 运行日志 (⚠️ gitignore)
│   ├── custom-pages/                 ← 手工维护的静态页面 (deploy.sh cp 到 /var/www/site/web/)
│   │   ├── index.html                ← 搜索型首页 (暗色模式, Mobile 全屏搜索)
│   │   ├── 404.html                  ← 自定义 404 (暗色模式)
│   │   ├── opensearch.xml            ← 浏览器 OpenSearch 配置
│   │   └── tools/
│   │       └── claudeek.html         ← Claudeek 产品页
│   └── scripts/                      ← Python 脚本集
│       ├── .env                      ← 环境变量 (⚠️ gitignore, 含生产密钥)
│       ├── pantools_export.xlsx      ← 资源数据源 Excel (⚠️ gitignore)
│       ├── pantools_export_seo.xlsx  ← AI 生成 SEO 后的输出 (⚠️ gitignore)
│       ├── database.db               ← SQLite 数据库 (⚠️ gitignore, VPS 上约 4.5MB)
│       ├── pantools_sync.py          ← Excel → SQLite 同步脚本
│       ├── auto_generate.py          ← 全站静态 HTML 生成引擎
│       ├── ai_seo_writer.py          ← AI SEO 描述批量生成器
│       ├── check_dead_links.py       ← 死链检测脚本 (每周一 3am)
│       ├── backup.sh                 ← 数据备份脚本
│       ├── check_ssl.sh              ← SSL 证书监控
│       └── templates/                ← Jinja2 网页模板
│           ├── layout.html           ← 基础布局（header/footer）
│           ├── detail.html           ← 资源详情页
│           ├── list.html             ← 资源列表页
│           └── transit.html          ← 跳转中转页（倒计时）
│
├── var/                              ← 可变数据 (⚠️ 整体 gitignore)
│   └── www/
│       ├── site/web/                 ← 生成的静态网站 (VPS 上由 auto_generate.py 生成)
│       │   ├── index.html            ← 首页 (deploy.sh 从 custom-pages cp)
│       │   ├── 404.html              ← 自定义 404 (deploy.sh 从 custom-pages cp)
│       │   ├── opensearch.xml        ← OpenSearch (deploy.sh 从 custom-pages cp)
│       │   ├── list.html             ← 资源列表 (auto_generate.py)
│       │   ├── index.json            ← 资源数据 JSON (auto_generate.py)
│       │   ├── sitemap.xml           ← 搜索引擎地图 (auto_generate.py)
│       │   ├── static/page/          ← 资源详情 + 中转页 (auto_generate.py, ~1200+ pages)
│       │   ├── post/                 ← 旧博文 (遗留)
│       │   ├── category/             ← 旧分类 (遗留)
│       │   ├── tools/                ← 工具页面 (deploy.sh cp)
│       │   ├── download/             ← 下载托管文件 (VPS 手动管理)
│       │   ├── tag_edu/geek/movie/other.html ← 旧标签页 (遗留)
│       │   └── baidu_verify_codeva-*.html    ← 百度站长验证
│       └── bigprc_site/              ← 旧 MkDocs SEO 站 (仅保留 nginx_redirects.conf)
│           └── nginx_redirects.conf  ← Nginx 跳转规则输出 (auto_generate.py 写入)
│
├── templates/                        ← 旧模板目录 (废弃)
├── venv/                             ← Python 虚拟环境 (⚠️ gitignore)
├── usr/                              ← 系统备份文件 (VPS /usr)
└── templates/                        ← 备用
```

### 已弃用并删除的内容 (2026-07-14 清理)

以下内容曾在 repo 中但已确认弃用并移除：

| 路径 | 说明 |
|------|------|
| `var/www/bigprc_site/docs/` | MkDocs SEO 生成文章（学区房等） |
| `var/www/bigprc_site/ai_seo_writer.py` | 旧版 SEO 脚本 (MkDocs 输出) |
| `var/www/bigprc_site/data.csv` | 旧版数据源 |
| `var/www/bigprc_site/mkdocs.yml` | MkDocs 配置 |
| `var/www/bigprc_site/site/` | MkDocs 构建输出 |
| `var/www/seo_env/` | MkDocs Python 虚拟环境 |
| `root/scripts/env` | 旧 API 密钥文件 (已被 .env 替代) |
| `root/scripts/resources.csv` | 旧 CSV 数据源 |
| `root/scripts/cron_log.txt` | 旧 cron 日志 |
| 所有 `._*` AppleDouble 文件 | macOS 资源分支垃圾 (5,955 个) |

---

## 5. VPS 运行时拓扑

> 信息来源: 2026-07-14 实际审计

### 服务器规格

| 项目 | 值 |
|------|------|
| 主机名 | ubuntu-4gb-hel1-17 (Hetzner) |
| IP | 37.27.246.3 |
| SSH | 端口 2222 |
| OS | Ubuntu 24.04 |
| CPU/RAM | 2 vCPU / 3.7 GB |
| 磁盘 | 38 GB (53% 使用) |
| 面板 | 1Panel (端口 31145) + Sui (端口 4433/55555/2096) |

### 端口映射

| 端口 | 服务 | 进程 | 说明 |
|------|------|------|------|
| 80 | Nginx | nginx (3 workers) | HTTP → 301 到 HTTPS |
| 443 | Nginx | nginx (3 workers) | HTTPS 主入口 |
| 2222 | SSH | sshd | 管理登录 |
| 18789 | Docker Proxy | docker-proxy → OpenClaw | 控制台 WebSocket 网关 |
| 3000 | Docker Proxy | docker-proxy → new-api/sub2api | AI API 本地代理 |
| 3306 | Docker Proxy | docker-proxy → MySQL | 数据库 (仅 localhost) |
| 8080 | Docker Proxy | docker-proxy | Docker 服务 |
| 8081 | Docker Proxy | docker-proxy | Docker 服务 |
| 8088 | Docker Proxy | docker-proxy | 授权引擎 API (api.bigprc.com 代理目标) |
| 2096 | Sui | sui | 面板组件 |
| 31145 | 1Panel | 1panel | 服务器管理面板 |
| 4433 | Sui | sui | 面板组件 |
| 55555 | Sui | sui | 面板组件 |

### Nginx 站点 → 后端映射

```
                    ┌─────────────────────────────┐
                    │         Nginx :80/:443       │
                    └─────────────────────────────┘
                                    │
        ┌───────────┬───────────────┼───────────────┬───────────┐
        ▼           ▼               ▼               ▼           ▼
  bigprc.com  claw.bigprc.com  www.bigprc.com  api.bigprc.com  其他
  :443            :80/:443        :443            :443
        │           │               │               │
        ▼           ▼               ├─ / → 静态文件  ├─ / → :8088
   :18789       :18789              ├─ /ws → :18789  └─ /api/kick → :9000
  (OpenClaw)   (OpenClaw)           ├─ /jump/ → 302
                                    ├─ /go/ → rewrite
                                    └─ /static/ → 静态
```

### 关键 Docker 容器

| 端口 | 推测服务 |
|------|---------|
| :18789 | OpenClaw Gateway (Node.js) |
| :3000 | new-api / sub2api (AI API 统一代理) |
| :3306 | MySQL |
| :8080 | 其他 Web 服务 |
| :8081 | 其他 Web 服务 |
| :8088 | 授权引擎 API |

### Cron 定时任务 (VPS 实际 crontab)

```
30 1 * * *  /usr/bin/python3 /root/scripts/pantools_sync.py >> /root/scripts/logs/cron.log 2>&1
32 1 * * *  /usr/bin/python3 /root/scripts/ai_seo_writer.py >> /root/scripts/logs/cron.log 2>&1
35 1 * * *  /usr/bin/python3 /root/scripts/auto_generate.py >> /root/scripts/logs/cron.log 2>&1
0 2 * * *   /root/scripts/backup.sh
0 9 * * *   /root/scripts/check_ssl.sh
0 3 * * 1   /usr/bin/python3 /root/scripts/check_dead_links.py
```

**执行顺序**: 数据同步(1:30) → AI SEO(1:32) → 页面生成+百度推送(1:35) → 备份(2:00) → SSL检查(9:00) → 死链检查(每周一3:00)

---

## 6. 环境搭建（一次性）

### Windows（PowerShell）

```powershell
cd "E:\Claudeek\Projects\bigprc configs"
.\setup.ps1
```

脚本自动完成：
1. 检测 Python 是否安装，若无则通过 winget 或 python.org 下载安装 Python 3.12
2. 在项目根目录创建 `venv` 虚拟环境
3. 安装依赖包：`jinja2` `python-dotenv` `requests` `openpyxl` `openai`

### macOS / Linux

```bash
cd /path/to/bigprc-configs
bash setup.sh
```

### 手动安装依赖

```bash
# Windows
python -m venv venv
.\venv\Scripts\python.exe -m pip install jinja2 python-dotenv requests openpyxl openai

# macOS/Linux
python3 -m venv venv
venv/bin/python3 -m pip install jinja2 python-dotenv requests openpyxl openai
```

---

## 7. 日常开发流程

### 标准工作流（6 步走）

```
编辑 Excel ──▶ 同步到数据库 ──▶ (可选) AI SEO ──▶ 生成静态站点 ──▶ 本地预览 ──▶ 推送 GitHub
```

#### 第 1 步：编辑资源数据

打开 `root\scripts\pantools_export.xlsx`，维护以下列：

| 列名 | 说明 | 必填 |
|------|------|------|
| 文件名 | 资源标题 | ✅ |
| 链接 | 普通下载链接（网盘地址） | 至少一个 |
| 短链 | 短链接（可选，用于移动端分享） | 否 |
| 文件大小 | 如 `2.3GB` | 否 |
| SEO简介 | 搜索引擎描述文案（可留空由 AI 生成） | 否 |

#### 第 2 步：同步到 SQLite 数据库

```powershell
.\venv\Scripts\python.exe root\scripts\pantools_sync.py
```

> 此脚本将 Excel 数据清洗后存入 `database.db`。支持增量更新（UPSERT），重复执行不会产生重复数据。

#### 第 3 步（可选）：AI 批量生成 SEO 描述

```powershell
# 处理 10 条
.\venv\Scripts\python.exe root\scripts\ai_seo_writer.py 10

# 处理全部
.\venv\Scripts\python.exe root\scripts\ai_seo_writer.py all
```

> 需要确保 `root/scripts/.env` 中配置了有效的 `API_BASE_URL` 和 `API_KEY`。
> 模型自动轮询：`deepseek-v4-flash` → `deepseek-v4-pro` → `deepseek-v4-pro[1]`。

#### 第 4 步：生成静态网站

```powershell
.\venv\Scripts\python.exe root\scripts\auto_generate.py
```

此脚本执行：
- 从 SQLite 数据库读取全部资源
- 为每个资源随机关联 4 个"猜你喜欢"（内链蜘蛛网）
- **多线程并发**（10 workers）渲染详情页、普通中转页、短链中转页
- 生成列表页 `list.html`
- 生成 `sitemap.xml`
- 生成 `index.json`（供列表页异步加载）
- 更新 Nginx 跳转规则 `nginx_redirects.conf`
- 尝试向百度推送新链接（本地环境会自动跳过）

#### 第 5 步：本地预览

```powershell
.\preview.ps1
```

- 启动 HTTP 服务器，监听 `127.0.0.1:8765`
- 自动打开浏览器
- 完整模拟线上 Nginx URL rewrite 规则
- `Ctrl+C` 停止

#### 第 6 步：提交到 GitHub

```powershell
git add -A
git commit -m "feat: 更新资源数据"
git push origin main
```

---

## 8. 脚本参考

### `pantools_sync.py` — Excel → SQLite 同步

| 项目 | 说明 |
|------|------|
| 输入 | `pantools_export.xlsx` |
| 输出 | `database.db` |
| 依赖 | `openpyxl`, `python-dotenv` |
| 配置 | `.env` 中的 `EXCEL_FILE` 和 `DB_FILE` |
| 表结构 | `resources(res_id TEXT PK, title, size, normal_url, short_url, seo_desc, category, platform, version, password, rating, sync_time, ai_generated)` |
| 行为 | UPSERT（新增或更新），以 `res_id`（如 `p001`）为主键 |
| VPS Cron | 每天 1:30 AM |

### `auto_generate.py` — 全站静态 HTML 生成引擎

| 项目 | 说明 |
|------|------|
| 输入 | SQLite 数据库 + Jinja2 模板 |
| 输出 | `var/www/site/web/` 下的全部 HTML |
| 配置 | `.env` 中的 11 个变量 |
| 并发 | 10 线程 |
| 功能 | ① 详情页生成 ② 中转页生成 ③ 列表页生成 ④ sitemap 生成 ⑤ Nginx 跳转规则生成 ⑥ 百度 SEO 推送 |
| 本地行为 | 百度推送和 Nginx 更新自动跳过（通过 try/except 保护） |
| VPS Cron | 每天 1:35 AM |

**生成的页面类型：**

| 文件命名 | 内容 | 示例 |
|---------|------|------|
| `{res_id}.html` | 资源详情页 | `p001.html` |
| `{res_id}_transit.html` | 普通链接中转页 | `p001_transit.html` |
| `{res_id}_short_transit.html` | 短链中转页 | `p001_short_transit.html` |

### `ai_seo_writer.py` — AI SEO 描述批量生成器

| 项目 | 说明 |
|------|------|
| 用法 | `python ai_seo_writer.py [数字\|all]` |
| 输入 | `pantools_export.xlsx` + `database.db` |
| 输出 | `pantools_export_seo.xlsx` + 写入 `database.db` |
| API | `API_BASE_URL` + `API_KEY` (来自 .env 的 new-api/sub2api 地址) |
| 模型轮询 | `deepseek-v4-flash` → `deepseek-v4-pro` → `deepseek-v4-pro[1]` |
| 缓存 | 已有合格 SEO 描述的条目（DB 中 >200 字 + 含 `<p>`）自动跳过 |
| 验证 | 字数 100-450、含 HTML `<p>` 标签、中文占比 >60%、无违禁品牌词、无 AI 拒绝语 |
| VPS Cron | 每天 1:32 AM |

### `check_dead_links.py` — 死链检测

| 项目 | 说明 |
|------|------|
| 输入 | database.db 中的所有网盘链接 |
| 输出 | `dead_links_report.txt` + `dead_links_check.log` |
| 检测 | HTTP 请求 + 页面关键词匹配（"分享已取消""文件已删除"等） |
| VPS Cron | 每周一凌晨 3:00 |

### `backup.sh` — 数据备份

| 项目 | 说明 |
|------|------|
| 备份内容 | Excel + SQLite + Nginx 配置 + 模板 + 自定义页面 |
| 保留策略 | 7 天 |
| 输出 | `/root/backups/bigprc_backup_YYYYMMDD_HHMMSS.tar.gz` |
| 日志 | `/root/scripts/backup.log` |
| VPS Cron | 每天 2:00 AM |

### `check_ssl.sh` — SSL 证书监控

| 项目 | 说明 |
|------|------|
| 检测 | Let's Encrypt 证书有效期 |
| 告警 | 剩余不足 14 天时发邮件 |
| 日志 | `/root/scripts/ssl_check.log` |
| VPS Cron | 每天 9:00 AM |

### `local_server.py` — 本地预览服务器

| 项目 | 说明 |
|------|------|
| 端口 | `8765`（可通过参数修改） |
| 绑定 | `127.0.0.1`（仅本机可访问） |
| 模拟规则 | `/` → index.html，`/go/{id}` → detail page，`/site/{path}` → static file，`/jump/*` → 提示页 |

### `deploy.sh` — VPS 一键部署脚本

| 项目 | 说明 |
|------|------|
| 运行位置 | VPS 上 `/root/bigprc-deploy/` |
| 命令 | `bash deploy.sh` / `bash deploy.sh rollback [N]` |
| 步骤 | 6 步：git pull → Nginx 软链接 → snippets → Python 脚本 → cp custom-pages → reload |
| 安全机制 | Nginx 语法检查失败阻止重载并报错 |

---

## 9. Nginx 配置说明

### 站点配置总览

| 文件 | 域名 | 端口 | 功能 |
|------|------|------|------|
| `sites-available/default` | `www.bigprc.com` | 443 | 主站：静态文件 + /ws 代理 + /jump/ 跳转 + /go/ rewrite + rate limit |
| `sites-available/openclaw` | `bigprc.com` | 80/443 | 裸域 HTTPS 跳转 + OpenClaw 反向代理 (:18789) |
| `sites-available/claw` | `claw.bigprc.com` | 80/443 | OpenClaw 控制台代理 |
| `sites-available/api.bigprc.com` | `api.bigprc.com` | 443 | 授权引擎 /api (:8088) + 顶号接口 /api/kick (:9000) |

### 主站配置详解（`default` — www.bigprc.com）

```
┌─────────────────────────────────────────────────────────────┐
│ server block: www.bigprc.com (443 SSL)                      │
│   root: /var/www/site/web                                   │
│   index: index.html                                         │
│                                                             │
│  /baidu_verify_codeva-*.html  →  百度验证直出               │
│  /ws                          →  proxy 127.0.0.1:18789     │
│  /ws/                         →  proxy 127.0.0.1:18789/    │
│  /jump/*                      →  include jump_rules.conf    │
│                                   Referer 防盗链            │
│  /go/*                        →  rewrite /static/page/*.html│
│  /static/                     →  静态文件 (7d cache)        │
│  /*.json|css|js               →  immutable cache (1y)       │
│  /                            →  try_files → 404.html       │
│  error_page 404               →  /404.html                  │
└─────────────────────────────────────────────────────────────┘
```

### 跳转规则 (`snippets/jump_rules.conf`)

由 `auto_generate.py` 自动生成，约 1,260 条资源 × 2 = 2,500+ 行 rewrite 规则：

```nginx
rewrite ^/jump/p001$ https://pan.quark.cn/s/xxxxx redirect;
rewrite ^/jump/p001_short$ https://link.pantools.cn/s/xxxxx redirect;
```

- **每条资源 1-2 条** rewrite 规则（普通链接 + 短链）
- **由脚本自动管理**，不可手动编辑
- `deploy.sh` 会跳过此文件（由 VPS 上 auto_generate.py 管理）
- 本地预览中 `/jump/*` 请求会返回提示信息（不执行实际跳转）

### 安全防护配置

#### Nginx Rate Limiting

| 路径 | 限制 | 突发 | 超限返回 |
|------|------|------|---------|
| `/go/*` (资源详情) | 10 次/秒/IP | burst 20 | HTTP 429 |
| `/jump/*` (跳转) | 10 次/秒/IP | burst 20 | HTTP 429 |
| `/ws` (WebSocket) | 5 次/秒/IP | burst 10 | HTTP 429 |

配置位置：`etc/nginx/nginx.conf` (zone 定义) + `etc/nginx/sites-available/default` (location 调用)

#### Security Headers (CSP)

见 `etc/nginx/snippets/security_headers.conf`：
- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `Content-Security-Policy` (含 `unsafe-inline` 因全站内联 CSS/JS)
- `Referrer-Policy: strict-origin-when-cross-origin`

---

## 10. 运维自动化

### 数据备份

**脚本位置**: `root/scripts/backup.sh`
**cron**: 每天 2:00 AM
**备份内容**: Excel + SQLite + Nginx 配置 + 模板 + 自定义页面
**保留策略**: 最近 7 天
**备份位置**: `/root/backups/bigprc_backup_YYYYMMDD_HHMMSS.tar.gz`
**日志**: `/root/scripts/backup.log`

**恢复备份**:
```bash
cd /root/backups
tar xzf bigprc_backup_YYYYMMDD_HHMMSS.tar.gz -C /tmp/restore/
cp /tmp/restore/pantools_export.xlsx /root/scripts/
cp /tmp/restore/database.db /root/scripts/
```

### SSL 证书监控

**脚本位置**: `root/scripts/check_ssl.sh`
**cron**: 每天 9:00 AM
**日志**: `/root/scripts/ssl_check.log`

**当前证书状态**:

| 域名 | 到期时间 | 剩余 |
|------|---------|------|
| bigprc.com | 2026-08-26 | ~43 天 |
| www.bigprc.com | 2026-08-26 | ~43 天 |
| api.bigprc.com | 2026-09-17 | ~65 天 |

### 死链检测

**脚本位置**: `root/scripts/check_dead_links.py`
**cron**: 每周一凌晨 3:00
**输出**: `/root/scripts/dead_links_report.txt`

---

## 11. 部署流程

### 首次部署（VPS 初始化）

```bash
# 1. SSH 登录 VPS
ssh -p 2222 root@37.27.246.3

# 2. 克隆仓库
git clone https://github.com/chiangprc/bigprc-deploy.git /root/bigprc-deploy

# 3. 运行部署
cd /root/bigprc-deploy
bash deploy.sh
```

### 日常更新部署

```bash
ssh -p 2222 root@37.27.246.3
cd /root/bigprc-deploy
bash deploy.sh
```

### 紧急回滚

```bash
cd /root/bigprc-deploy
bash deploy.sh rollback      # 回滚 1 个提交
bash deploy.sh rollback 3    # 回滚 3 个提交
```

### 部署脚本执行流程

```
deploy.sh (共 6 步)

[1/6] git pull origin main             ← 拉取最新
[2/6] ln -sf Nginx sites-available     ← 所有 site 配置软链接到
     + ln -sf Nginx sites-enabled        /etc/nginx/sites-*/ 和 /etc/nginx/nginx.conf
[3/6] ln -sf Nginx snippets             ← 代码片段（跳过 jump_rules.conf）
[4/6] ln -sf Python 脚本 & 模板         ← 软链接到 /root/scripts/ 和 /root/scripts/templates/
[5/6] cp 手工静态页面                    ← root/custom-pages/ → /var/www/site/web/
                                          （用 cp 非 ln，因 Nginx www-data 无法穿透 /root/）
[6/6] nginx -t && systemctl reload      ← 语法检查通过后热重载
      pkill openclaw && nohup 重启      ← 重启 OpenClaw 网关
```

### 软链接策略

VPS 上仓库路径与系统目录的映射：

```
仓库                                        ──软链接──▶   系统路径
etc/nginx/sites-available/default          ──▶  /etc/nginx/sites-available/default
                                                        └──▶ /etc/nginx/sites-enabled/default
etc/nginx/nginx.conf                       ──▶  /etc/nginx/nginx.conf
root/scripts/auto_generate.py              ──▶  /root/scripts/auto_generate.py
root/scripts/templates/detail.html         ──▶  /root/scripts/templates/detail.html
```

> **特殊情况**: `ai_seo_writer.py` 在 VPS 上为**直接文件**（非 symlink），因为它在 cron 中被单独调用且可能经过手动修改。deploy.sh 步骤 4 会 symlink 所有 .py 文件，但 VPS 上手动覆盖过。

---

## 12. 模板系统

### 模板文件

| 模板 | 用途 | 关键变量 |
|------|------|---------|
| `layout.html` | 基础 HTML 框架（head/meta/结构化数据/百度统计/Clarity） | `title`, `canonical_url`, `clarity_id` |
| `detail.html` | 资源详情页 | `title`, `seo_desc`, `size`, `res_id`, `normal_url`, `short_url`, `drive_name`, `related_resources` |
| `list.html` | 资源列表页 | `resources[]` |
| `transit.html` | 跳转中转页（倒计时） | `title`, `jump_id`, `admin_email` |

### 模板变量说明

**detail.html 接收变量：**

```python
{
    "title": "资源标题",
    "seo_desc": "SEO 描述（HTML 格式）",
    "size": "2.3GB",
    "res_id": "p001",
    "normal_url": "https://pan.quark.cn/s/xxxxx",
    "short_url": "https://link.pantools.cn/s/xxxxx",
    "drive_name": "夸克网盘",     # 自动识别
    "admin_email": "admin@bigprc.com",
    "clarity_id": "微软 Clarity 分析 ID",
    "canonical_url": "https://www.bigprc.com/go/p001",
    "related_resources": [...]    # 4 个随机关联资源
}
```

### 网盘智能识别引擎

`auto_generate.py` 内置了 **12 种网盘** 的 URL 模式匹配：

| 网盘名称 | 匹配域名 |
|---------|---------|
| 夸克网盘 | `quark.cn` |
| 百度网盘 | `baidu.com` |
| 阿里云盘 | `alipan.com` / `aliyundrive.com` |
| 迅雷网盘 | `xunlei.com` |
| 123 网盘 | `123pan.com` / `123pan.cn` |
| 天翼云盘 | `189.cn` |
| 蓝奏云 | `lanzou*.com` |
| 115 网盘 | `115.com` |
| UC 网盘 | `uc.cn` |
| 腾讯微云 | `weiyun.com` |
| 诚通网盘 | `ctfile.com` |
| 移动云盘 | `10086.cn` |
| （默认） | "极速转存" |

---

## 13. 环境变量参考

### `.env` 文件（VPS: `/root/scripts/.env`）

> ⚠️ 此文件在 `.gitignore` 中排除，不推送 GitHub。
> 本地 repo 中的版本是开发模板（含占位符），VPS 版本含真实生产配置。

```ini
# New API / sub2api 本地代理地址 (ai_seo_writer.py 使用)
API_BASE_URL=http://127.0.0.1:3000/v1
API_KEY=sk-xxxxxxxx

# 数据文件路径
EXCEL_FILE=/root/scripts/pantools_export.xlsx
DB_FILE=/root/scripts/database.db

# 生成页面输出路径
PAGE_DIR=/var/www/site/web/static/page
INDEX_FILE=/var/www/site/web/list.html
SITEMAP_FILE=/var/www/site/web/sitemap.xml

# Nginx 跳转规则输出路径
NGINX_CONF_FILE=/var/www/bigprc_site/nginx_redirects.conf

# 站点配置
DOMAIN=https://www.bigprc.com
BAIDU_TOKEN=xxxxxxxx          # 百度搜索资源平台推送令牌
PUSHED_LOG_FILE=/root/scripts/pushed_urls.log
ADMIN_EMAIL=admin@bigprc.com
```

### bashrc API 密钥矩阵（VPS: `/root/.bashrc`）

> ⚠️ 此文件在 `.gitignore` 中排除。包含 OpenClaw 及 AI 流水线所需的环境变量。

| 变量 | 用途 |
|------|------|
| `GROQ_API_KEY` | Groq API |
| `CF_API_TOKEN` / `CF_ACCOUNT_ID` | Cloudflare API |
| `GEMINI_API_KEY` | Google Gemini |
| `VOLC_API_KEY` / `VOLC_ENDPOINT_ID` | 火山引擎（豆包） |
| `QWEN_API_KEY` | 阿里云通义千问 |
| `DEEPSEEK_API_KEY` | DeepSeek |
| `OPENAI_BASE_URL` / `OPENAI_API_KEY` / `OPENAI_MODEL` | OpenAI 兼容配置（指向 DeepSeek） |
| `NVM_DIR` | Node.js 版本管理（OpenClaw 依赖） |

---

## 14. Git 管理策略

### 提交规则

| 类型 | 是否推送 | 说明 |
|------|---------|------|
| Python 脚本 (`.py`) | ✅ 推送 | 核心逻辑 |
| Nginx 配置 (`etc/nginx/*`) | ✅ 推送 | 服务器配置 |
| Jinja2 模板 (`.html`) | ✅ 推送 | 网站外观 |
| 部署/设置脚本 (`.sh`, `.ps1`) | ✅ 推送 | 自动化脚本 |
| 本地服务器 (`local_server.py`) | ✅ 推送 | 本地预览 |
| 手工静态页面 (`root/custom-pages/`) | ✅ 推送 | 首页、404、工具页等 |
| 生成的 HTML (`var/`) | ❌ gitignore | VPS 上由 auto_generate.py 生成 |
| 数据库 (`*.db`) | ❌ gitignore | 本地/生产数据 |
| Excel 数据 (`*.xlsx`) | ❌ gitignore | 资源数据 |
| Python 环境 (`venv/`) | ❌ gitignore | 环境隔离 |
| `.env` 文件 | ❌ gitignore | 含密钥 |
| `bashrc` | ❌ gitignore | 含 API 密钥 |
| SSL 证书 (`etc/letsencrypt/`) | ❌ gitignore | VPS 上 Let's Encrypt 管理 |
| Nginx jump rules | ❌ gitignore | auto_generate.py 自动生成 |
| 日志文件 (`*.log`) | ❌ gitignore | 运行时日志 |
| `preview.ps1` | ❌ gitignore | 仅本地使用 |

### .gitignore 核心规则

```ini
# 密钥 & 环境变量
.env / *.env / **/scripts/.env / **/scripts/env

# 数据库 & 数据
*.db / *.xlsx / *.csv

# 自动生成
**/snippets/jump_rules.conf / var/

# Python 环境
**/seo_env/ / **/venv/ / **/__pycache__/

# SSL 证书
/etc/letsencrypt/

# Shell 配置（含密钥）
.bashrc / bashrc

# 日志
*.log / *.log.*

# 系统垃圾
._* / .DS_Store / Thumbs.db
```

### 分支策略

- **main** — 唯一分支，直接推送
- 仓库地址：`https://github.com/chiangprc/bigprc-deploy`

---

## 15. VPS ↔ 本地同步指南

### 同步原则

- **VPS 为运行时权威源** — 端口、进程、实际文件结构以 VPS 为准
- **本地 repo 为配置源** — 脚本、模板、Nginx 配置在本地编辑，push 后 VPS deploy
- **生成文件不同步** — `var/www/site/web/` 下的 HTML 在 VPS 上由 cron 自动生成

### 审计命令

使用 `vps_audit.sh` 一键收集 VPS 完整状态：

```bash
# VPS 上
bash /root/bigprc-deploy/vps_audit.sh
```

### 常见同步场景

**场景 1: 从 VPS 拉取新文件到本地**
```bash
# VPS 上 cat 文件内容，本地手动写入
# 适用于小型配置文件（nginx configs, custom pages 等）
```

**场景 2: 本地修改推送到 VPS**
```bash
# 本地
git add -A && git commit -m "..." && git push origin main

# VPS 上
cd /root/bigprc-deploy && git pull && bash deploy.sh
```

**场景 3: VPS 上有手动修改需要回传**
```bash
# VPS 上查看差异
cd /root/bigprc-deploy && git status
# 复制文件内容到本地，本地写入后 commit + push
# 下次 VPS deploy 时会被覆盖为 repo 版本
```

---

## 16. 常见问题排查

### Q: `.\preview.ps1` 报错 "Generated site not found"

**原因**：还没有生成网站文件。
**解决**：先运行 `.\venv\Scripts\python.exe root\scripts\auto_generate.py`

### Q: `pantools_sync.py` 报错 "Excel 读取失败"

**原因**：`pantools_export.xlsx` 不存在或格式错误。
**解决**：确认 `root\scripts\pantools_export.xlsx` 存在，第一行是表头。

### Q: 本地预览时 `/jump/p001` 不跳转

**正常行为**：本地预览中 `/jump/*` 被禁用，避免调试时误跳转外部链接。

### Q: `auto_generate.py` 报 "数据库为空"

**原因**：`database.db` 中没有数据。
**解决**：先运行 `pantools_sync.py` 导入 Excel 数据。

### Q: 部署后网站不更新

排查步骤：
1. 确认 `git push` 成功推送到 GitHub
2. SSH 登录 VPS，`cd /root/bigprc-deploy && git log -1` 查看是否最新
3. 如果 VPS 上代码是旧的：手动 `git pull`
4. 检查 auto_generate.py 是否运行过（cron 每天 1:35，或手动执行 `python3 /root/scripts/auto_generate.py`）
5. `nginx -t && systemctl status nginx`

### Q: 部署后 Nginx 报错

```bash
# VPS 上
nginx -t                          # 语法检查
systemctl status nginx            # 服务状态
tail -f /var/log/nginx/error.log  # 错误日志
```

### Q: Nginx 报 "conflicting server name"

**原因**：同一域名在多个 server block 中定义。最常见是 `sites-enabled/` 下有重复文件。
**解决**: `ls -la /etc/nginx/sites-enabled/` 检查是否有同名或冲突配置，删除重复项后 `systemctl reload nginx`。

### Q: 网站返回 HTTP 403（Nginx Permission denied）

**原因**：Nginx worker（www-data）无法访问 site/web 文件。
**解决**：重跑 deploy.sh 步骤 5，确保 custom-pages 用 cp 而非 ln 复制：
```bash
cd /root/bigprc-deploy && bash deploy.sh
ls -la /var/www/site/web/index.html  # 应显示 -rw-r--r--（普通文件）
```

### Q: 网站返回 HTTP 522（Cloudflare 报错）

**原因**：Cloudflare 无法连接 VPS 源站。
**排查步骤**：
1. Ping VPS IP 确认可达
2. `curl -I -k https://127.0.0.1/ -H "Host: www.bigprc.com"` 在 VPS 上验证本地 Nginx
3. 检查 Hetzner Cloud Firewall 是否放行 TCP 80/443
4. 检查 Cloudflare DNS A 记录指向正确 IP
5. Cloudflare SSL/TLS 模式设为 Full 或 Full (strict)

### Q: 部署后手工静态页面没生效

**原因**：旧软链接未清除，cp 报 "same file"。
**解决**：
```bash
cd /root/bigprc-deploy && git pull && bash deploy.sh
ls -la /var/www/site/web/index.html  # 应显示 -rw-r--r--
```

### Q: 如何验证线上网站正常

```bash
curl -I https://www.bigprc.com        # 主站 (应 200)
curl -I https://claw.bigprc.com       # 控制台
curl -I https://api.bigprc.com        # API
curl -I https://www.bigprc.com/go/p001  # 资源详情
```

### Q: VPS 上的 cron 任务是否正常

```bash
crontab -l                          # 列出所有 cron
cat /root/scripts/logs/cron.log     # 流水线日志
cat /root/scripts/backup.log        # 备份日志
cat /root/scripts/dead_links_report.txt  # 死链报告
```

---

## 附录 A：依赖清单

| 包名 | 版本要求 | 用途 |
|------|---------|------|
| Python | ≥ 3.9（推荐 3.12） | 脚本运行时 |
| jinja2 | latest | HTML 模板渲染 |
| python-dotenv | latest | .env 环境变量加载 |
| requests | latest | HTTP 请求（百度推送） |
| openpyxl | latest | Excel 文件读写 |
| openai | latest | AI SEO 生成（仅 ai_seo_writer.py） |

---

## 附录 B：版本历史

| 日期 | 变更 |
|------|------|
| 2026-07-14 | VPS-Local 全量审计同步；新增 api.bigprc.com；删除弃用文件；修正 .env 变量；更新 cron 任务；移除 claw.conf 冲突；新增 Section 5 (VPS 拓扑) 和 Section 15 (同步指南) |
| 2026-06-22 | 初始版本 |

---

> 📝 如有疑问或需要补充，请联系项目维护者或在 GitHub 提 Issue。
> 🤖 本文档由 Claude Code 根据项目源代码和 VPS 审计结果生成。

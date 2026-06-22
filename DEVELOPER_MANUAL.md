# BigPRC 开发者手册

> **站点**: https://www.bigprc.com  
> **仓库**: https://github.com/chiangprc/bigprc-deploy  
> **最后更新**: 2026-06-21

---

> 🔴 **日常操作看这里 → [WORKFLOW_DAILY.md](WORKFLOW_DAILY.md)**  
> 本文档是完整的系统架构和配置参考。日常改页面、更新资源、部署上线等操作，请优先查阅《开发者日常工作流》。

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [目录结构](#3-目录结构)
4. [环境搭建（一次性）](#4-环境搭建一次性)
5. [日常开发流程](#5-日常开发流程)
6. [脚本参考](#6-脚本参考)
7. [Nginx 配置说明](#7-nginx-配置说明)
8. [运维自动化](#8-运维自动化)
9. [部署流程](#9-部署流程)
10. [模板系统](#10-模板系统)
11. [环境变量参考](#11-环境变量参考)
12. [Git 管理策略](#12-git-管理策略)
13. [常见问题排查](#13-常见问题排查)

---

## 1. 项目概述

BigPRC 是一个**极客资源聚合分享站**——从 Excel 数据源读取资源列表，通过 Python 脚本自动生成全站静态 HTML，部署到 Nginx + Ubuntu VPS 上对外服务。

### 核心技术栈

| 层 | 技术 | 用途 |
|---|------|------|
| 数据层 | Excel (.xlsx) → SQLite | 资源数据存储与清洗 |
| 生成层 | Python 3.12 + Jinja2 | 静态 HTML 页面批量渲染 |
| AI 辅助 | OpenAI 兼容 API | 自动生成 SEO 描述文案 |
| 服务器 | Ubuntu + Nginx | 静态站点托管 + 反向代理 |
| 网关 | OpenClaw (Node.js) | 管理控制台 WebSocket 代理 |
| 版本控制 | Git + GitHub | 配置与脚本的版本管理 |
| 部署 | Bash deploy.sh | 软链接 + Nginx 热重载 |

### 页面 URL 路由规则

| URL 模式 | 对应内容 | 实现方式 |
|----------|---------|---------|
| `/` | 首页 (index.html) | 静态文件 |
| `/list.html` | 资源列表页 | Jinja2 生成 |
| `/go/{res_id}` | 资源详情页（如 `/go/p001`） | Nginx rewrite → `/static/page/p001.html` |
| `/jump/{res_id}` | 普通链接中转跳转 | Nginx include jump_rules.conf → 302 重定向 |
| `/jump/{res_id}_short` | 短链中转跳转 | 同上 |
| `/site/{path}` | 站点静态资源 | try_files 回退 |
| `/ws` | WebSocket | 反向代理到 OpenClaw :18789 |

### 线上域名体系

```
bigprc.com        ─── 裸域，301 → www + OpenClaw 反向代理
www.bigprc.com    ─── 主站（静态资源展示）
claw.bigprc.com   ─── OpenClaw 管理控制台
```

---

## 2. 系统架构

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
│  (可选)       │          ai_seo_writer.py                 │  Web Server  │
└──────────────┘                                            └──────┬───────┘
                                                                   │
                                                             ┌─────▼──────┐
                                                             │  用户浏览器  │
                                                             └────────────┘
```

### 开发→部署流水线

```
本地电脑                            GitHub                          VPS 服务器
─────────                         ────────                         ──────────
1. 编辑 Excel
2. pantools_sync.py  ─┐
3. auto_generate.py   ├─▶ git push ──▶ github.com/             ──▶ git pull
4. preview.ps1 预览   ─┘               chiangprc/bigprc-deploy      bash deploy.sh
                                                                   (软链接 + 热重载)
```

---

## 3. 目录结构

```
bigprc configs/                       ← 项目根目录
│
├── deploy.sh                         ← VPS 部署脚本（在服务器上执行）
├── setup.sh / setup.ps1              ← 本地环境初始化（一次性）
├── preview.sh / preview.ps1          ← 本地预览服务器启动脚本
├── local_server.py                   ← 本地 HTTP 服务器（模拟 Nginx rewrite）
├── .gitignore                        ← 推送排除清单
│
├── etc/                              ← 服务器配置文件
│   ├── nginx/
│   │   ├── nginx.conf                ← Nginx 主配置
│   │   ├── sites-available/
│   │   │   ├── default               ← www.bigprc.com 主站
│   │   │   ├── claw                  ← claw.bigprc.com 控制台
│   │   │   └── openclaw              ← bigprc.com 裸域 + 网关代理
│   │   └── snippets/
│   │       ├── jump_rules.conf       ← 自动生成的跳转规则（⚠️ 不推送）
│   │       ├── fastcgi-php.conf
│   │       └── snakeoil.conf
│   └── letsencrypt/                  ← SSL 证书配置
│       ├── cli.ini
│       ├── options-ssl-nginx.conf
│       └── ssl-dhparams.pem
│
├── root/                             ← VPS 上的 /root 目录内容
│   ├── bashrc                        ← VPS shell 配置（含 API 密钥）
│   ├── openclaw.log                  ← OpenClaw 运行日志
│   └── scripts/                      ← Python 脚本集
│       ├── .env                      ← 本地开发环境变量
│       ├── env                       ← API 密钥（New API 地址和 token）
│       ├── pantools_export.xlsx      ← 📊 资源数据源（Excel）
│       ├── pantools_export_seo.xlsx  ← AI 生成 SEO 后的输出
│       ├── pantools_sync.py          ← Excel → SQLite 同步脚本
│       ├── auto_generate.py          ← 全站静态 HTML 生成引擎
│       ├── ai_seo_writer.py          ← AI SEO 描述批量生成器
│       ├── database.db               ← SQLite 数据库（本地不推送）
│       ├── resources.csv             ← 资源 CSV 备用数据
│       ├── cron_log.txt              ← 定时任务日志
│       └── templates/                ← Jinja2 网页模板
│           ├── layout.html           ← 基础布局（header/footer）
│           ├── detail.html           ← 资源详情页
│           ├── list.html             ← 资源列表页
│           └── transit.html          ← 跳转中转页（倒计时）
│
├── var/                              ← 可变数据（⚠️ 整体不推送 Git）
│   ├── www/
│   │   ├── site/web/                 ← 生成的静态网站
│   │   │   ├── index.html            ← 首页
│   │   │   ├── list.html             ← 资源列表
│   │   │   ├── sitemap.xml           ← 搜索引擎地图
│   │   │   ├── static/page/          ← 资源详情 + 中转页
│   │   │   ├── tools/                ← 工具页面
│   │   │   └── post/                 ← 博客文章
│   │   ├── bigprc_site/              ← 站点原始数据/MkDocs 文档
│   │   ├── html/                     ← 默认 html 目录（空）
│   │   └── seo_env/                  ← SEO Python 虚拟环境
│   └── log/                          ← 系统日志快照
│
└── venv/                             ← Python 虚拟环境（⚠️ 不推送）
    ├── Scripts/python.exe            ← Python 解释器
    └── Lib/site-packages/            ← 已安装的包
```

---

## 4. 环境搭建（一次性）

### Windows（PowerShell）

```powershell
cd "Z:\Claudeek\Projects\bigprc configs"
.\setup.ps1
```

脚本自动完成：
1. 检测 Python 是否安装，若无则通过 winget 或 python.org 下载安装 Python 3.12
2. 在项目根目录创建 `venv` 虚拟环境
3. 安装依赖包：`jinja2` `python-dotenv` `requests`

### macOS / Linux

```bash
cd /path/to/bigprc-configs
bash setup.sh
```

脚本自动完成：
1. 检测 Python 是否安装，若无则通过 Homebrew 或 python.org 下载安装
2. 创建 `venv` 虚拟环境
3. 安装依赖包

### 手动安装依赖

如果自动脚本失败，可手动执行：

```bash
# Windows
python -m venv venv
.\venv\Scripts\python.exe -m pip install jinja2 python-dotenv requests

# macOS/Linux
python3 -m venv venv
venv/bin/python3 -m pip install jinja2 python-dotenv requests
```

---

## 5. 日常开发流程

### 标准工作流（5 步走）

```
编辑 Excel ──▶ 同步到数据库 ──▶ 生成静态站点 ──▶ 本地预览 ──▶ 推送 GitHub
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

> 需要确保 `root/scripts/env` 中配置了有效的 API 地址和密钥。模型会自动轮询 fallback 列表：`deepseek-v4-flash` → `deepseek-v4-pro` → `deepseek-v4-pro[1]`。

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
- 尝试更新 Nginx 跳转规则（本地环境会自动跳过）
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

## 6. 脚本参考

### `pantools_sync.py` — Excel → SQLite 同步

| 项目 | 说明 |
|------|------|
| 输入 | `root/scripts/pantools_export.xlsx` |
| 输出 | `root/scripts/database.db` |
| 依赖 | `openpyxl`, `python-dotenv` |
| 表结构 | `resources(res_id TEXT PK, title, size, normal_url, short_url, seo_desc, sync_time)` |
| 行为 | UPSERT（新增或更新），以 `res_id`（如 `p001`）为主键 |

### `auto_generate.py` — 全站静态 HTML 生成引擎

| 项目 | 说明 |
|------|------|
| 输入 | SQLite 数据库 + Jinja2 模板 |
| 输出 | `var/www/site/web/` 下的全部 HTML |
| 并发 | 10 线程 |
| 功能 | ① 详情页生成 ② 中转页生成 ③ 列表页生成 ④ sitemap 生成 ⑤ Nginx 规则更新 ⑥ 百度 SEO 推送 |
| 本地行为 | 百度推送和 Nginx 更新自动跳过（通过 try/except 保护） |

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
| 输入 | `pantools_export.xlsx` |
| 输出 | `pantools_export_seo.xlsx` |
| 依赖 | `openai` SDK, `openpyxl` |
| 模型轮询 | `deepseek-v4-flash` → `deepseek-v4-pro` → `deepseek-v4-pro[1]` |
| 缓存 | 已有合格 SEO 描述的条目自动跳过 |
| 验证 | 字数 ≥300、含 HTML 标签、中文占比 >60%、无违禁品牌词、无 AI 拒绝语 |

### `local_server.py` — 本地预览服务器

| 项目 | 说明 |
|------|------|
| 端口 | `8765`（可通过参数修改） |
| 绑定 | `127.0.0.1`（仅本机可访问，无法从局域网访问） |
| 模拟的 Nginx 规则 | `/` → index.html，`/go/{id}` → detail page，`/site/{path}` → static file，`/jump/*` → 提示页 |

### `deploy.sh` — VPS 一键部署脚本

| 项目 | 说明 |
|------|------|
| 运行位置 | VPS 服务器上 `/root/bigprc-deploy/` |
| 前提 | 已通过 `git clone` 拉取仓库 |
| 步骤 | git pull → Nginx 站点配置软链接 → Nginx snippets 软链接 → Python 脚本软链接 → Nginx 语法检查 + 热重载 → OpenClaw 重启 |
| 安全机制 | Nginx 语法检查失败会阻止重载并报错退出 |

---

## 7. Nginx 配置说明

### 站点配置总览

| 文件 | 域名 | 功能 |
|------|------|------|
| `sites-available/default` | `www.bigprc.com` | 主站：静态文件 + WebSocket + 跳转规则 |
| `sites-available/claw` | `claw.bigprc.com` | OpenClaw 管理控制台代理 |
| `sites-available/openclaw` | `bigprc.com` | 裸域 HTTPS 转发 + 网关反向代理 |

### 主站配置详解（`default`）

```
┌─────────────────────────────────────────────────────┐
│ server block: www.bigprc.com (443 SSL)              │
│                                                     │
│  /baidu_verify_codeva-*.html  →  百度验证直出       │
│  /ws                          →  127.0.0.1:18789   │
│  /jump/*                       →  include jump_rules.conf │
│  /                             →  try_files → /index.html │
│  /go/*                         →  rewrite → /static/page/*.html │
│  /static/                      →  静态文件目录         │
└─────────────────────────────────────────────────────┘
```

### 跳转规则 (`snippets/jump_rules.conf`)

由 `auto_generate.py` 自动生成，格式为：

```nginx
rewrite ^/jump/p001$ https://pan.baidu.com/s/xxxxx redirect;
rewrite ^/jump/p001_short$ https://t.cn/xxxxx redirect;
```

- **每条资源 1-2 条** rewrite 规则（普通链接 + 短链）
- **由脚本自动管理**，不可手动编辑
- `deploy.sh` 会跳过此文件（因为它在 VPS 上由 cron/auto_generate.py 管理）
- 本地预览中 `/jump/*` 请求会返回提示信息（不执行实际跳转）

### 安全防护配置

#### Nginx Rate Limiting

站点在 Nginx 层配置了双层速率限制：

| 路径 | 限制 | 突发 | 超限返回 |
|------|------|------|---------|
| `/go/*` (资源详情) | 10 次/秒/IP | burst 20 | HTTP 429 |
| `/jump/*` (跳转) | 10 次/秒/IP | burst 20 | HTTP 429 |
| `/ws` (WebSocket) | 5 次/秒/IP | burst 10 | HTTP 429 |

配置位置：`etc/nginx/nginx.conf` (zone 定义) + `etc/nginx/sites-available/default` (location 调用)

#### Security Headers (CSP)

全站启用以下安全头：
- `X-Frame-Options: SAMEORIGIN` — 防点击劫持
- `X-Content-Type-Options: nosniff` — 防 MIME 嗅探
- `Content-Security-Policy` — 限制脚本/样式/图片来源（因全站内联 CSS/JS，需 `unsafe-inline`）
- `Referrer-Policy: strict-origin-when-cross-origin` — 控制 Referer 传递

配置位置：`etc/nginx/snippets/security_headers.conf`

#### Cloudflare 补充防护

在 Cloudflare Dashboard 可额外配置：

1. **Rate Limiting Rules** (Security → WAF → Rate Limiting Rules):
   - 路径 `/go/*`：100 次/10 秒 → JS Challenge
   - 路径 `/jump/*`：100 次/10 秒 → JS Challenge
2. **Bot Fight Mode** (Security → Bots)：开启，自动拦截已知爬虫
3. **Security Level** (Security → Settings)：设为 Medium

---

## 8. 运维自动化

### 数据备份

每日备份通过 cron 定时任务执行，备份以下内容：
- Excel 资源数据 (`pantools_export.xlsx`)
- SQLite 数据库 (`database.db`)
- Nginx 配置文件
- Jinja2 模板
- 自定义静态页面

```bash
# 在 VPS 上首次配置
ssh -p 2222 root@37.27.246.3

# 添加 crontab 任务
crontab -e
# 添加: 0 2 * * * /root/scripts/backup.sh
```

**备份位置**: `/root/backups/`（保留最近 7 天）  
**脚本位置**: `/root/scripts/backup.sh`  
**日志位置**: `/root/scripts/backup.log`

**恢复备份**:
```bash
cd /root/backups
tar xzf bigprc_backup_20260622_020000.tar.gz -C /tmp/restore/
# 复制需要的文件回原位
cp /tmp/restore/pantools_export.xlsx /root/scripts/
cp /tmp/restore/database.db /root/scripts/
```

**远程备份（可选）**:
```bash
# 在 crontab 中配置 rsync 远程同步:
0 2 * * * REMOTE_UPLOAD="user@backup-server:/backups/bigprc" /root/scripts/backup.sh
```

### SSL 证书监控

每日检查 Let's Encrypt 证书有效期，剩余不足 14 天时发送邮件告警：

```bash
# 在 VPS 上首次配置
crontab -e
# 添加: 0 9 * * * /root/scripts/check_ssl.sh
```

**脚本位置**: `/root/scripts/check_ssl.sh`  
**日志位置**: `/root/scripts/ssl_check.log`

如需邮件告警，先安装 mailutils：
```bash
apt install mailutils
```

### Uptime 监控

BigPRC 通过 [UptimeRobot](https://uptimerobot.com)（免费版）进行外部可用性监控。

**初次设置步骤**：

1. 注册账号：https://uptimerobot.com/signUp
2. 添加监控项：
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: BigPRC Main Site
   - **URL**: `https://www.bigprc.com`
   - **Monitoring Interval**: 5 minutes
3. 添加第二个监控：
   - **URL**: `https://claw.bigprc.com`
   - 同上设置
4. 配置告警联系方式：
   - Email: `admin@bigprc.com`
   - 可选添加 Telegram/Discord Webhook

**免费版限制**：50 个监控、5 分钟检查间隔、3 个月日志保留。对于当前需求完全足够。

**故障排查**：
- 如果 UptimeRobot 报告宕机但你自己能访问，可能是 Cloudflare 回源问题 → 检查 VPS 状态
- 如果持续宕机 → SSH 登录 VPS 检查：`systemctl status nginx`

---

## 9. 部署流程

### 首次部署（VPS 初始化）

```bash
# 1. SSH 登录 VPS
ssh root@<服务器IP>

# 2. 克隆仓库
git clone https://github.com/chiangprc/bigprc-deploy.git /root/bigprc-deploy

# 3. 运行部署
cd /root/bigprc-deploy
bash deploy.sh
```

### 日常更新部署

```bash
ssh root@<服务器IP>
cd /root/bigprc-deploy
bash deploy.sh
```

### 部署脚本做了什么

```
deploy.sh 执行流程（共 6 步）：

[1/6] git pull origin main             ← 拉取最新配置和脚本
[2/6] ln -sf Nginx 站点配置             ← 将仓库中的配置软链接到 /etc/nginx/sites-available/
                                          同时软链接到 /etc/nginx/sites-enabled/
[3/6] ln -sf Nginx snippets             ← 软链接代码片段（跳过 jump_rules.conf）
[4/6] ln -sf Python 脚本 & 模板         ← 软链接到 /root/scripts/ 和 /root/scripts/templates/
[5/6] cp 手工静态页面                    ← 复制 root/custom-pages/ 到 /var/www/site/web/
                                          （用 cp 而非 ln，因为 Nginx www-data 无法穿透 /root/）
[6/6] nginx -t && systemctl reload      ← 语法检查通过后热重载
      pkill openclaw && nohup 重启      ← 重启 OpenClaw 网关
```

### 软链接策略说明

仓库内文件与系统目录的映射关系：

```
仓库路径                                        ──软链接──▶   系统路径
etc/nginx/sites-available/default              ──▶  /etc/nginx/sites-available/default
                                                        └──▶ /etc/nginx/sites-enabled/default
root/scripts/auto_generate.py                  ──▶  /root/scripts/auto_generate.py
root/scripts/templates/detail.html             ──▶  /root/scripts/templates/detail.html
```

> **为什么要用软链接？**
> 1. 修改仓库文件 = 修改生效文件，无需 cp/rsync
> 2. Nginx 语法检查失败时可以回滚（git checkout）
> 3. 所有变更受 Git 版本控制

---

## 10. 模板系统

### 模板文件

| 模板 | 用途 | 关键变量 |
|------|------|---------|
| `layout.html` | 基础 HTML 框架（head/meta/结构化数据/百度统计/Clarity） | `title`, `canonical_url`, `clarity_id` |
| `detail.html` | 资源详情页 | `title`, `seo_desc`, `size`, `res_id`, `normal_url`, `short_url`, `drive_name`, `related_resources` |
| `list.html` | 资源列表页 | `resources[]` |
| `transit.html` | 跳转中转页（5秒倒计时 + 广告展示） | `title`, `jump_id`, `admin_email` |

### 模板变量说明

**detail.html 接收变量：**

```python
{
    "title": "资源标题",
    "seo_desc": "SEO 描述（HTML 格式）",
    "size": "2.3GB",
    "res_id": "p001",
    "normal_url": "https://pan.baidu.com/s/xxxxx",  # 可能为 None
    "short_url": "https://t.cn/xxxxx",                # 可能为 None
    "drive_name": "百度网盘",                          # 自动识别
    "admin_email": "admin@bigprc.com",
    "clarity_id": "微软 Clarity 分析 ID",
    "canonical_url": "https://www.bigprc.com/go/p001",
    "related_resources": [...]                         # 4 个随机关联资源
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
| （默认） | "专属专线" |

---

## 11. 环境变量参考

### 本地 `.env` 文件（`root/scripts/.env`）

```ini
DB_FILE=root/scripts/database.db
PAGE_DIR=var/www/site/web/static/page
INDEX_FILE=var/www/site/web/list.html
SITEMAP_FILE=var/www/site/web/sitemap.xml
NGINX_CONF_FILE=var/www/bigprc_site/nginx_redirects.conf
DOMAIN=https://www.bigprc.com
BAIDU_TOKEN=local_dev_skip
DAILY_PUSH_QUOTA=100
PUSHED_LOG_FILE=root/scripts/pushed_urls.log
ADMIN_EMAIL=admin@bigprc.com
CLARITY_ID=local_dev
```

### API 密钥文件（`root/scripts/env`）

```ini
API_BASE_URL=http://127.0.0.1:3000/v1
API_KEY=sk-xxxxxxxx
```

### VPS 环境变量（`/root/scripts/.env`）

VPS 上需要一个**独立的** `.env` 文件（不推送 Git），包含真实的：

- `BAIDU_TOKEN` — 百度搜索资源平台推送令牌
- `CLARITY_ID` — 微软 Clarity 分析真实 ID
- 其他生产环境配置

### VPS Shell 环境（`/root/.bashrc` / 仓库中 `root/bashrc`）

包含多个 AI API 密钥：
- `GROQ_API_KEY` — Groq
- `CF_API_TOKEN` / `CF_ACCOUNT_ID` — Cloudflare
- `GEMINI_API_KEY` — Google Gemini
- `VOLC_API_KEY` — 火山引擎（豆包）
- `QWEN_API_KEY` — 阿里云通义千问
- `DEEPSEEK_API_KEY` — DeepSeek

> ⚠️ 这些密钥在 `.gitignore` 中排除，不会被推送到 GitHub。

---

## 12. Git 管理策略

### 提交规则

| 类型 | 是否推送 | 说明 |
|------|---------|------|
| Python 脚本 (`.py`) | ✅ 推送 | 核心逻辑 |
| Nginx 配置 (`.conf`, `sites-available/*`) | ✅ 推送 | 服务器配置 |
| Jinja2 模板 (`.html`) | ✅ 推送 | 网站外观 |
| 部署/设置脚本 (`.sh`, `.ps1`) | ✅ 推送 | 自动化脚本 |
| 本地服务器 (`local_server.py`) | ✅ 推送 | 本地预览 |
| 手工静态页面 (`root/custom-pages/`) | ✅ 推送 | 首页、工具页等手工维护的页面 |
| 生成的 HTML (`var/www/site/`) | ❌ 不推送 | 自动生成，VPS 上独立生成 |
| 数据库 (`*.db`) | ❌ 不推送 | 本地数据 |
| Python 环境 (`venv/`) | ❌ 不推送 | 环境隔离 |
| `.env` / `env` 文件 | ❌ 不推送 | 含密钥 |
| `bashrc` | ❌ 不推送 | 含 API 密钥 |
| SSL 证书 (`etc/letsencrypt/`) | ❌ 不推送 | VPS 上由 Let's Encrypt 管理 |
| `preview.ps1` | ❌ 不推送 | 仅本地使用 |

### 分支策略

- **main** — 唯一分支，直接推送
- 仓库地址：`https://github.com/chiangprc/bigprc-deploy`

---

## 13. 常见问题排查

### Q: `.\preview.ps1` 报错 "Generated site not found"

**原因**：还没有生成网站文件。  
**解决**：先运行 `.\venv\Scripts\python.exe root\scripts\auto_generate.py`

### Q: `pantools_sync.py` 报错 "Excel 读取失败"

**原因**：`pantools_export.xlsx` 不存在或格式错误。  
**解决**：确认 `root\scripts\pantools_export.xlsx` 存在，第一行是表头（文件名、链接、短链、文件大小、SEO简介）。

### Q: 本地预览时 `/jump/p001` 不跳转

**正常行为**：本地预览中 `/jump/*` 被禁用，会显示提示："External redirect disabled in local preview"。这是为了避免本地调试时误跳转到外部链接。

### Q: `auto_generate.py` 报 "数据库为空"

**原因**：`database.db` 中没有数据。  
**解决**：先运行 `pantools_sync.py` 导入 Excel 数据。

### Q: 部署后网站不更新

排查步骤：
1. 确认 `git push` 成功推送到 GitHub
2. SSH 登录 VPS，`cd /root/bigprc-deploy && git log -1` 查看是否最新提交
3. 如果 VPS 上代码是旧的：手动 `git pull`
4. 如果代码已是最新但网站不变：检查 VPS 上的 `auto_generate.py` 是否运行过（可能需要 cron 定时任务触发）
5. 检查 Nginx 是否正常：`nginx -t && systemctl status nginx`

### Q: 部署后 Nginx 报错

```bash
# 在 VPS 上检查
nginx -t                          # 语法检查
systemctl status nginx            # 服务状态
tail -f /var/log/nginx/error.log  # 错误日志
```

### Q: 如何验证线上网站正常

```bash
curl -I https://www.bigprc.com        # 主站（应返回 200）
curl -I https://claw.bigprc.com       # 控制台
curl -I https://www.bigprc.com/go/p001  # 某个资源页面
```

### Q: VPS 上的 `.env` 如何配置

```bash
# SSH 登录 VPS 后
nano /root/scripts/.env
```

填入真实的生产环境配置（参考第 11 节的变量列表），保存后重新运行 `auto_generate.py`。

### Q: 网站返回 HTTP 522（Cloudflare 报错）

**原因**：Cloudflare 无法连接到 VPS 源站。  
**排查步骤**：
1. 确认 VPS 是否在运行：Ping 服务器 IP
2. 在 VPS 上验证本地 Nginx 正常：`curl -I -k https://127.0.0.1/ -H "Host: www.bigprc.com"`（应返回 200）
3. 检查 **Hetzner 云防火墙**（独立于 VPS 内 ufw）：在 Hetzner Cloud Console → Firewalls 中确认已放行 TCP 80 和 443
4. 检查 Cloudflare DNS A 记录是否指向正确的 VPS IP
5. 检查 Cloudflare SSL/TLS 模式是否设为 **Full** 或 **Full (strict)**

### Q: 网站返回 HTTP 403（Nginx Permission denied）

**原因**：Nginx worker 进程（www-data 用户）无法访问站点文件。  
**常见场景**：
- 文件是软链接指向 `/root/` 路径 → www-data 无法穿透 `/root/`（权限 700）
- 文件权限设为 600 或目录缺少执行权限

**解决**：
```bash
# 检查文件是否为软链接
ls -la /var/www/site/web/index.html
# 如果是 lrwxrwxrwx 且指向 /root/，需要改为真实文件
rm /var/www/site/web/index.html
cp /root/bigprc-deploy/root/custom-pages/index.html /var/www/site/web/index.html

# 或直接重跑 deploy.sh（v1f826fa+ 已修复为 cp）
cd /root/bigprc-deploy && git pull && bash deploy.sh
```

### Q: 从外部无法访问 VPS 但 VPS 本地 curl 正常

**原因**：VPS 提供商可能有独立的云防火墙（如 Hetzner Cloud Firewall、AWS Security Group、阿里云安全组）。  
**排查**：
1. `nc -zv <VPS_IP> 443` 在本地测试 TCP 是否可达
2. `curl -I -k --resolve www.bigprc.com:443:<VPS_IP> https://www.bigprc.com/` 绕开 Cloudflare 直连测试
3. 如果 TCP 能通但 TLS 握手超时，大概率是云防火墙拦截
4. 前往 VPS 提供商控制台检查防火墙入站规则

### Q: 部署后手工静态页面没生效

**原因**：
1. VPS 上旧版本 deploy.sh 用了 `ln -sf`（软链接），www-data 无法穿透 `/root/`
2. 旧软链接没被清除，`cp` 报 "same file" 错误退出

**解决**：确保 VPS 上 deploy.sh 版本 ≥ `1f826fa`：
```bash
cd /root/bigprc-deploy && git pull && bash deploy.sh
ls -la /var/www/site/web/index.html  # 应显示 -rw-r--r--（普通文件）
```

### Q: 部署后网站异常，如何紧急回滚？

**原因**：新部署的配置或代码引入了问题。  
**解决**：使用 deploy.sh 内置回滚命令：

```bash
# SSH 登录 VPS
ssh -p 2222 root@37.27.246.3
cd /root/bigprc-deploy

# 回滚到上一个版本
bash deploy.sh rollback

# 回滚到更早的版本（如回滚 3 个提交）
bash deploy.sh rollback 3
```

**回滚原理**：
1. `git reset --hard HEAD~N` 将仓库文件恢复到历史版本
2. 由于 Nginx 配置和 Python 脚本都是软链接指向仓库，会自动跟随更新
3. 重新执行部署步骤（symlink + cp custom-pages + nginx reload）
4. Nginx 语法检查失败会阻止回滚，确保不会雪上加霜

**局限性**：
- 仅能回滚 Git 跟踪的配置和脚本，不能回滚自动生成的 HTML 文件
- 不能回滚 SQLite 数据库
- 如有未提交的 VPS 本地修改，回滚会丢失这些修改

---

## 附录 A：日常操作

> 🔴 **完整版操作指南请查阅 → [WORKFLOW_DAILY.md](WORKFLOW_DAILY.md)**

**本地预览：** `.\preview.ps1`  
**推送到 GitHub：** `git push origin main`  
**VPS 部署：** `ssh -p 2222 root@37.27.246.3` → `cd /root/bigprc-deploy && bash deploy.sh`

---

## 附录 B：依赖清单

| 包名 | 版本要求 | 用途 |
|------|---------|------|
| Python | ≥ 3.9（推荐 3.12） | 脚本运行时 |
| jinja2 | latest | HTML 模板渲染 |
| python-dotenv | latest | .env 环境变量加载 |
| requests | latest | HTTP 请求（百度推送） |
| openpyxl | latest | Excel 文件读写 |
| openai | latest | AI SEO 生成（仅 ai_seo_writer.py） |

---

> 📝 如有疑问或需要补充，请联系项目维护者或在 GitHub 提 Issue。  
> 🤖 本文档由 Claude Code 根据项目源代码自动生成。

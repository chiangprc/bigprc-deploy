# BigPRC 项目结构手册

> 最后更新: 2026-06-22  
> 文件总数: 60+  
> 仓库地址: github.com/chiangprc/bigprc-deploy

本手册列出项目中**每一个文件**的用途和说明，按目录分组。

---

## 根目录

| 文件 | 用途 | 维护方式 |
|------|------|---------|
| **README.md** | 项目索引手册。架构总览、文档导航、技术栈、路由表、快速命令 | 手动编辑 |
| **DEVELOPER_MANUAL.md** | 开发者使用手册。完整系统架构、数据流、脚本说明、环境变量、故障排查 | 手动编辑 |
| **WORKFLOW_DAILY.md** | 日常工作流与维护手册。一分钟命令、文件地图、常见问题、服务器信息 | 手动编辑 |
| **deploy.sh** | VPS 一键部署脚本。git pull → 软链接部署 → Nginx 重载 → OpenClaw 重启。支持 `rollback [N]` 参数回滚 | Git 管理 |
| **local_server.py** | 本地预览 HTTP 服务器。模拟 Nginx URL rewrite（/go/, /jump/, /tools/, /sitemap.xml 等路由）| Git 管理 |
| **setup.ps1** | Windows 本地环境安装脚本。检测 Python → 创建 venv → 安装依赖 | Git 管理 |
| **setup.sh** | macOS/Linux 本地环境安装脚本。同上 | Git 管理 |
| **preview.ps1** | Windows 本地预览启动脚本。检测 Python → 验证依赖 → 启动 local_server.py | Git 管理 |
| **preview.sh** | macOS/Linux 本地预览启动脚本。同上 | Git 管理 |
| **.gitignore** | Git 排除规则。排除 venv/、数据库、证书、API 密钥、生成文件 | Git 管理 |

---

## etc/ — 服务器配置文件

### etc/nginx/

| 文件 | 用途 |
|------|------|
| **nginx.conf** | Nginx 主配置。worker_processes、gzip（压缩级别 6、vary on）、limit_req_zone（/go/ 10r/s, /jump/ 10r/s, /ws 5r/s）、limit_req_status 429 | 
| **fastcgi.conf** | FastCGI 标准参数（遗留，未使用）|

### etc/nginx/sites-available/ → 软链接到 /etc/nginx/sites-enabled/

| 文件 | 域名 | 功能 |
|------|------|------|
| **default** | www.bigprc.com | 主站配置。SSL 终结、安全头 include、Cache-Control 分层（HTML 1h / 静态 7d）、/ws WebSocket 代理、/jump/ 302 + Referer 防盗链、/go/ rewrite、/static/ 文件服务、/tools/ 自定义页面、error_page 404 |
| **claw** | claw.bigprc.com | OpenClaw 管理控制台反向代理（:18789）|
| **openclaw** | bigprc.com | 裸域 HTTPS 转发 + OpenClaw 网关代理 |

### etc/nginx/snippets/

| 文件 | 用途 |
|------|------|
| **security_headers.conf** | 安全头集合。CSP、X-Frame-Options SAMEORIGIN、X-Content-Type-Options nosniff、X-XSS-Protection、Referrer-Policy、Permissions-Policy |
| **jump_rules.conf** | 自动生成的 302 跳转规则。由 auto_generate.py 管理，每条 rewrite 对应一个资源的网盘链接 |
| **fastcgi-php.conf** | PHP FastCGI 配置（遗留，未使用）|
| **snakeoil.conf** | 自签名 SSL 回退配置 |

### etc/letsencrypt/

| 文件/目录 | 用途 |
|----------|------|
| **cli.ini** | Certbot 命令行配置 |
| **options-ssl-nginx.conf** | Mozilla 推荐的 SSL 参数（TLS 版本、加密套件）|
| **ssl-dhparams.pem** | DH 密钥交换参数 |
| **live/bigprc.com/** | 裸域 SSL 证书（cert.pem, chain.pem, fullchain.pem, privkey.pem）|
| **live/www.bigprc.com/** | www 子域 SSL 证书 |
| **updated-*-digest.txt** | Certbot 更新检查摘要文件 |

---

## root/ — VPS /root/ 目录镜像

### root/ 根

| 文件 | 用途 | Git |
|------|------|-----|
| **bashrc** | VPS shell 配置。含 Groq/Cloudflare/Gemini/Volc/Qwen/DeepSeek API 密钥 | 不推送 |
| **openclaw.log** | OpenClaw 网关运行日志 | 不推送 |

### root/custom-pages/ → cp 到 /var/www/site/web/

| 文件 | 用途 | 维护 |
|------|------|------|
| **index.html** | 首页。搜索框 + 移动端 .is-searching 接管 + 分类标签 + Claudeek 卡片 + noscript | 手动 |
| **404.html** | 自定义 404 页面。扁平纯文字，暗色模式 | 手动 |
| **opensearch.xml** | OpenSearch 描述文件。支持浏览器地址栏直接搜索 BigPRC | 手动 |
| **tools/claudeek.html** | Claudeek 产品售卖页。功能列表、定价、版本对比、FAQ | 手动 |

### root/scripts/ — Python 脚本与数据

#### 核心脚本

| 文件 | 用途 | 依赖 |
|------|------|------|
| **auto_generate.py** | 全站静态 HTML 生成引擎。① 多线程渲染详情页+中转页 ② 生成 index.json ③ 生成列表页 ④ 生成分类标签页 ⑤ 生成 sitemap.xml ⑥ 更新 Nginx 跳转规则 ⑦ 百度 SEO URL 推送 | jinja2, requests, dotenv |
| **pantools_sync.py** | Excel → SQLite 同步脚本。读取 Excel 数据 → 清洗 → UPSERT 到数据库。支持 11 列（title/size/urls/seo/category/platform/version/password/rating/ai_generated）| openpyxl, dotenv |
| **ai_seo_writer.py** | AI SEO 描述批量生成器。调 OpenAI 兼容 API（DeepSeek），批量生成资源 SEO 文案。含内容验证（≥300 字、含 HTML、中文 >60%、无违禁词）| openai, openpyxl |
| **check_dead_links.py** | 死链自动检测脚本。HEAD+GET 请求所有 URL，模式匹配检测死链状态。输出报告并可邮件通知 | requests |

#### 运维脚本

| 文件 | 用途 |
|------|------|
| **backup.sh** | 每日数据备份。打包 Excel + SQLite + Nginx 配置 + 模板 → tar.gz，保留 7 天，可选 rsync 远程 |
| **check_ssl.sh** | SSL 证书过期检查。openssl 读取到期日，< 14 天发送邮件告警 |

#### 数据文件

| 文件 | 用途 | Git |
|------|------|-----|
| **pantools_export.xlsx** | 资源主数据。列：文件名/链接/短链/文件大小/SEO简介/资源类型/适用平台/版本号/解压密码/推荐星级/AI生成 | 不推送 |
| **pantools_export_seo.xlsx** | AI SEO 生成后的输出文件 | 不推送 |
| **database.db** | SQLite 数据库。表 resources（res_id PK, title, size, normal_url, short_url, seo_desc, category, platform, version, password, rating, ai_generated, sync_time）| 不推送 |
| **resources.csv** | CSV 备用数据源 | 不推送 |

#### 配置文件

| 文件 | 用途 | Git |
|------|------|-----|
| **.env** | 项目环境变量。DB_FILE, PAGE_DIR, DOMAIN, BAIDU_TOKEN, CLARITY_ID 等 | 不推送 |
| **env** | AI API 密钥。API_BASE_URL, API_KEY | 不推送 |

#### 日志

| 文件 | 用途 |
|------|------|
| **cron_log.txt** | 定时任务执行日志 |
| **pushed_urls.log** | 已推送百度的 URL 记录（防重复推送）|
| **backup.log** | 备份脚本运行日志 |
| **ssl_check.log** | SSL 证书检查日志 |
| **dead_links_check.log** | 死链检测日志 |
| **dead_links_report.txt** | 死链检测报告 |

### root/scripts/templates/ — Jinja2 HTML 模板

| 模板 | 用途 | 关键变量 |
|------|------|---------|
| **layout.html** | 基础 HTML 框架。① `<head>` FOUC 防闪烁脚本 ② CSS 变量（亮/暗双主题）③ sticky 顶栏导航 ④ `:focus-visible` 全局焦点环 ⑤ 6px 扁平滚动条 ⑥ `@media print` 打印样式 ⑦ font-smoothing + text-rendering ⑧ OpenSearch + OG + favicon ⑨ trackEvent() 工具函数 | title, canonical_url, admin_email, clarity_id |
| **detail.html** | 资源详情页。① `<article>` 语义标签 ② 4 列信息网格（格式/大小/平台/版本）③ 实心 CTA 按钮 ④ AI 生成内容标识 ⑤ JSON-LD 结构化数据 ⑥ 死链反馈入口 ⑦ 相关资源推荐 ⑧ `<data>` / `<time>` 语义标签 | title, seo_desc, size, res_id, normal_url, short_url, drive_name, category, platform, version, password, rating, ai_generated, related_resources |
| **list.html** | 资源列表页。① `<main>` 语义标签 ② fetch /index.json 异步加载 ③ 动态分类标签筛选 ④ 客户端分页（30 条/页）⑤ 实时搜索过滤 ⑥ `?q=` URL 参数支持 ⑦ 移动端 44px 触控热区 ⑧ noscript 降级 | resources, filter_category, admin_email, clarity_id |
| **transit.html** | 跳转中转页。① 5 秒倒计时 + 1px 进度条 CSS 动画 ② 标题"安全验证中"→"验证已通过"③ 按钮升起淡入微交互（opacity + translateY 0.4s）④ Clarity 事件埋点（transit_loaded, redirect_complete）| title, jump_id, admin_email, clarity_id, canonical_url |

---

## docs/ — 项目文档

| 文件 | 用途 |
|------|------|
| **PROJECT_STRUCTURE.md**（本文件）| 项目结构手册。全部 60+ 文件的用途说明 |
| **EVALUATION_AND_IMPROVEMENT_PLAN.md** | 全站评估与改进方案。26 项评估清单，每项含现状分析、改进方案、代码示例、工时估算。三阶段实施路线图 |
| **DESIGN_SPEC_FLAT_REDESIGN.md** | 扁平化重设计规范 v2.3。设计令牌、顶栏导航、CTA 按钮、首页搜索接管、详情页信息卡、中转页进度条、列表页、404 页。含 19 项专家评审意见（颜色对比度、FOUC、焦点状态、滚动条、打印样式、History API、OpenSearch、语义化 HTML 等）|

---

## var/ — 可变数据

### var/www/site/web/ — 生成的静态网站

由 `auto_generate.py` 生成，**不推送 Git**。

| 文件/目录 | 内容 | 数量 |
|----------|------|------|
| **index.json** | 全量资源 JSON 数据。浏览器异步拉取 + Preload 预加载 | 1 文件, ~150KB |
| **index.html** | 首页（从 custom-pages 复制）| 1 文件 |
| **list.html** | 资源列表页 | 1 文件 |
| **sitemap.xml** | XML 站点地图 | 1 文件 |
| **static/page/\*.html** | 资源详情页 + 中转页 | ~3,800 文件 |
| **tag_\*.html** | 分类标签过滤页 | 按分类数量 |
| **tools/** | 工具页面（从 custom-pages 复制）| 2 文件 |
| **post/** | 博客文章（手动维护）| 若干 |
| **404.html** | 自定义 404（从 custom-pages 复制）| 1 文件 |
| **baidu_verify_\*.html** | 百度搜索资源平台验证文件 | 1 文件 |
| **download/** | 文件下载目录（Claudeek 安装包镜像）| 若干 |

### var/www/bigprc_site/ — MkDocs 文档站

辅助文档站点，使用 MkDocs Material 主题构建，**不推送 Git**。

| 文件/目录 | 用途 |
|----------|------|
| **mkdocs.yml** | MkDocs 配置 |
| **docs/** | Markdown 源文件 |
| **ai_seo_writer.py** | 该文档站的 AI SEO 生成器变体 |
| **data.csv** | 该文档站的数据源 |

### var/log/ — 系统日志快照

VPS 系统日志的本地备份副本。**不推送 Git**。

---

## 已推送 vs 不推送

| 推送到 GitHub | 不推送（VPS 本地/机密/生成）|
|--------------|---------------------------|
| Python 脚本 (.py) | database.db |
| Shell 脚本 (.sh, .ps1) | pantools_export.xlsx |
| Nginx 配置 (.conf) | .env / env（API 密钥）|
| Jinja2 模板 (.html) | bashrc（API 密钥）|
| 自定义静态页面 (custom-pages/) | SSL 证书 (etc/letsencrypt/) |
| 部署脚本 (deploy.sh) | 生成的 HTML (var/www/site/web/) |
| 本地服务器 (local_server.py) | venv/ |
| 文档 (.md) | jump_rules.conf（自动生成）|
| opensearch.xml | 日志文件 (.log) |
| 安全头片段 | openclaw.log |

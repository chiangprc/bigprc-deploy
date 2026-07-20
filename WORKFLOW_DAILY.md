# BigPRC 日常工作流与维护手册

> **如果你只记得一件事：** 手工页面改 `root/custom-pages/`，生成页面改 Excel 跑脚本。改完 `git push`，然后 VPS 跑 `cd /root/bigprc-deploy && bash deploy.sh && cd /root/scripts && python3 auto_generate.py`。
> 
> **v2 完整流水线：** Excel 更新 → `pantools_sync_v2.py` → `ai_classifier.py` → `ai_seo_writer.py` → `ai_tag_generator.py` → `collection_generator.py` → `collection_faq.py` → `auto_generate.py`。详见 [V2_UPGRADE_COMPLETED.md](docs/V2_UPGRADE_COMPLETED.md)。

---

## 一分钟速查

### 我改了模板或手工页面（首页、详情页、中转页、404 等）

```powershell
# 1. 本地重新生成 + 预览
cd "Z:\Claudeek\Projects\bigprc configs"
python root\scripts\auto_generate.py
python local_server.py 8765

# 2. 推送
git add -A && git commit -m "feat: xxx" && git push origin main
```

```bash
# 3. VPS 部署 + 重新生成（一行搞定）
ssh -p 2222 root@37.27.246.3
cd /root/bigprc-deploy && bash deploy.sh && cd /root/scripts && python3 auto_generate.py
```

### 我改了资源数据（新增/修改资源）

```powershell
# 1. 编辑 Excel
# 打开 root\scripts\pantools_export.xlsx，编辑资源数据

# 2. 同步到数据库
python root\scripts\pantools_sync.py

# 3. （可选）AI 生成 SEO
python root\scripts\ai_seo_writer.py 10    # 处理 10 条
python root\scripts\ai_seo_writer.py all   # 处理全部

# 4. 生成全站
python root\scripts\auto_generate.py

# 5. 本地预览
python local_server.py 8765

# 6. 推送
git add -A && git commit -m "feat: 更新资源" && git push origin main
```

### 我只改了 Nginx 配置

```powershell
git add -A && git commit -m "fix: nginx xxx" && git push origin main
```
```bash
ssh -p 2222 root@37.27.246.3
cd /root/bigprc-deploy && bash deploy.sh
```

---

## 关键提醒

### 页面类型速记

| 类型 | 位置 | 修改后需要 | 部署方式 |
|------|------|-----------|---------|
| 手工静态页面 | `root/custom-pages/` | 直接 git push | `deploy.sh` cp 到 web/ |
| Jinja2 模板 | `root/scripts/templates/` | 跑 `auto_generate.py` 重新生成 | `deploy.sh` ln -sf 到 /root/scripts/ |
| Python 脚本 | `root/scripts/*.py` | 直接 git push | `deploy.sh` ln -sf 到 /root/scripts/ |
| Nginx 配置 | `etc/nginx/` | 直接 git push | `deploy.sh` ln -sf 到 /etc/nginx/ |
| 资源数据 | `root/scripts/pantools_export.xlsx` | 跑 `pantools_sync.py` + `auto_generate.py` | 数据在 VPS 本地，不经过 Git |

### 本地 vs 线上差异

| 差异点 | 本地 | VPS |
|--------|------|-----|
| `/jump/*` 跳转 | local_server.py 显示提示 | Nginx 执行 302 |
| 百度 SEO 推送 | 自动跳过（try/except）| 实际推送 |
| Nginx 规则更新 | 自动跳过（try/except）| 实际更新 |
| index.json | 生成到 var/www/site/web/ | 生成到 /var/www/site/web/ |
| .env 路径 | 相对路径（root/scripts/）| 绝对路径（/root/scripts/）|

---

## 完整文件地图

| 改这里 | 不要碰这里 |
|--------|-----------|
| root/custom-pages/*.html | var/www/site/web/（自动生成）|
| root/scripts/templates/*.html | etc/nginx/snippets/jump_rules.conf（自动生成）|
| root/scripts/*.py | root/scripts/.env（含密钥）|
| etc/nginx/sites-available/ | etc/letsencrypt/（证书）|
| etc/nginx/nginx.conf | root/scripts/database.db（数据）|
| etc/nginx/snippets/security_headers.conf | root/scripts/pantools_export.xlsx（数据）|
| root/custom-pages/opensearch.xml | root/bashrc（含密钥）|
| deploy.sh | |
| local_server.py | |
| docs/*.md | |

---

## 常见问题 5 秒修复

| 现象 | 原因 | 修复 |
|------|------|------|
| 网站不更新 | VPS 没重新生成 | `cd /root/bigprc-deploy && bash deploy.sh && cd /root/scripts && python3 auto_generate.py` |
| 模板改了不生效 | 忘记跑 auto_generate.py | 先本地 `python root\scripts\auto_generate.py` 再推送 |
| 详情页标题不居中 | 生成文件是旧的 | 重新生成 |
| 搜索不出结果 | index.json 没更新 | 重新生成（auto_generate.py 会输出 index.json 大小）|
| 中转页倒计时不动 | trackEvent 未定义 | 确认 layout.html 已更新并重新部署 |
| 部署后网站异常 | 配置/代码有问题 | VPS 跑 `bash deploy.sh rollback` |
| 回滚多版本 | 需回到更早的版本 | VPS 跑 `bash deploy.sh rollback 3` |
| Nginx 语法错误 | 配置有 bug | deploy.sh 会自动阻止重载，检查 `nginx -t` 输出 |
| push 报认证错误 | GitHub token 过期 | 去 GitHub → Settings → Developer settings 换 token |
| 404 页面不触发 | try_files 回退到 index.html | 已修复为 `=404`，重新部署 |

---

## 定时任务

VPS crontab 配置：

```
# 每天凌晨 2:00 — 备份 Excel + SQLite + Nginx配置 + 模板（保留最近 7 天）
0 2 * * * /root/scripts/backup.sh

# 每天上午 9:00 — 检查 SSL 证书有效期，不足 14 天发邮件告警
0 9 * * * /root/scripts/check_ssl.sh

# 每周一凌晨 3:00 — 检测所有资源链接是否失效
0 3 * * 1 /usr/bin/python3 /root/scripts/check_dead_links.py
```

---

## 服务器信息

| 项目 | 值 |
|------|-----|
| 提供商 | Hetzner |
| 公网 IP | `37.27.246.3` |
| SSH 端口 | `2222`（不是默认的 22）|
| 仓库路径 | `/root/bigprc-deploy` |
| 网站目录 | `/var/www/site/web` |
| 脚本目录 | `/root/scripts` |
| 备份目录 | `/root/backups` |

### SSH 登录

```bash
ssh -p 2222 root@37.27.246.3
```

### 紧急回滚

```bash
ssh -p 2222 root@37.27.246.3
cd /root/bigprc-deploy
bash deploy.sh rollback     # 回滚到上一个版本
bash deploy.sh rollback 3   # 回滚 3 个版本
```

### 日常部署（一行）

```bash
ssh -p 2222 root@37.27.246.3 "cd /root/bigprc-deploy && bash deploy.sh && cd /root/scripts && python3 auto_generate.py"
```

---

## 监控与告警

| 工具 | 用途 | 配置位置 |
|------|------|---------|
| UptimeRobot | 网站可用性监控（5 分钟间隔）| uptimerobot.com |
| check_ssl.sh | SSL 证书过期告警（< 14 天）| VPS crontab |
| backup.sh | 数据每日备份（7 天保留）| VPS crontab |
| check_dead_links.py | 死链每周检测 | VPS crontab |
| Microsoft Clarity | 用户行为分析 + 热图 | layout.html 内嵌 |
| Cloudflare | CDN + DDoS 防护 | cloudflare.com |

---

## v2.0 AI 内容流水线 (全链路)

**完整升级文档**: [docs/V2_UPGRADE_COMPLETED.md](docs/V2_UPGRADE_COMPLETED.md)

### 资源更新后需依次执行

```bash
cd /root/scripts

# 1. Excel → DB 同步
python3 pantools_sync_v2.py

# 2. AI 资源分类 (category/platform/resource_type)
python3 ai_classifier.py

# 3. AI SEO 内容生成 (tagline/summary/keywords/reason)
python3 ai_seo_writer.py --round 1 --force
python3 ai_seo_writer.py --round 2 --force
python3 ai_seo_writer.py --audit    # 质量巡检

# 4. AI 标签提取 (tags + resource_tags)
python3 ai_tag_generator.py
python3 tag_normalize.py             # 归一化碎片标签

# 5. 专题刷新 (collections + resource_collections)
python3 collection_generator.py --rebuild
python3 collection_faq.py            # FAQ 生成

# 6. 全站静态生成
python3 auto_generate.py
```

### 质量维护

```bash
python3 ai_seo_writer.py --audit    # AI 内容质量报告
python3 ai_seo_writer.py --repair   # 自动修复违规词
python3 migration.py validate       # 数据库完整性
```

---

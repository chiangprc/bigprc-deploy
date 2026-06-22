# 🗓️ BigPRC 开发者日常工作流

> **如果你只记得一件事：** 手工页面改 `root/custom-pages/`，生成页面改 Excel 跑脚本。改完 `git push`，然后 VPS 跑 `bash deploy.sh`。

---

## ⚡ 一分钟速查

### 我改了手工页面（首页、工具页等）

```powershell
# 1. 本地预览确认
cd "Z:\Claudeek\Projects\bigprc configs"
.\preview.ps1

# 2. 推送
git add -A
git commit -m "feat: 更新 xxx 页面"
git push origin main
```

```bash
# 3. VPS 部署
ssh root@37.27.246.3
cd /root/bigprc-deploy && bash deploy.sh
```

### 我改了资源数据（新增/修改资源）

```powershell
# 1. 编辑 root\scripts\pantools_export.xlsx

# 2. 同步到数据库
.\venv\Scripts\python.exe root\scripts\pantools_sync.py

# 3. 生成网站
.\venv\Scripts\python.exe root\scripts\auto_generate.py

# 4. 预览
.\preview.ps1

# 5. 推送
git add -A
git commit -m "feat: 更新资源数据"
git push origin main
```

```bash
# 6. VPS 部署（同步配置和脚本）
ssh root@37.27.246.3
cd /root/bigprc-deploy && bash deploy.sh

# 7. VPS 上重新生成 HTML（如果 auto_generate.py 没配 cron）
python3 /root/scripts/auto_generate.py
```

---

## 🔴 三个必须记住的关键点

### ❗ 1. 两种页面，两种改法

| 页面类型 | 在哪里改 | Git 追踪？ | VPS 怎么更新 |
|---------|---------|-----------|------------|
| **手工页面**（首页 `index.html`、工具页 `claudeek.html` 等） | `root/custom-pages/` | ✅ 推送 | `deploy.sh` [5/6] 自动 `cp` 到 `/var/www/site/web/` |
| **生成页面**（资源详情页、列表页、中转页） | 改 Excel → 跑 `auto_generate.py` | ❌ 不推送 | VPS 上独立跑 `auto_generate.py` |

> ⚠️ **绝对不要直接改 `var/www/site/web/` 下的文件！** 它们要么是自动生成的（下次生成会覆盖），要么是软链接（不受 Git 管理）。

### ❗ 2. 本地预览 ≠ 线上网站

| 环境 | 命令 | 说明 |
|------|------|------|
| 本地预览 | `.\preview.ps1` | 127.0.0.1:8765，跳转功能禁用 |
| 线上网站 | `https://www.bigprc.com` | 通过 Cloudflare → VPS |

### ❗ 3. 两套防火墙，两套规则

```
你的 Mac ──▶ Hetzner 云防火墙 ──▶ VPS 内 ufw ──▶ Nginx
              ↑ 独立于 VPS         ↑ VPS 内的
              在 Hetzner 网页       ufw/iptables
              控制台配置            命令行配置
```

> 🔴 **改了端口或发现外部连不上，两套防火墙都要检查。**  
> Hetzner 控制台 → Firewalls → ssh-firewall → 入站规则  
> VPS 内：`ufw status`

---

## 📋 完整文件地图

```
项目根目录 Z:\Claudeek\Projects\bigprc configs

┌── 我该改哪些文件？ ──────────────────────────────┐
│                                                   │
│  改首页、工具页                                   │
│  → root/custom-pages/     【Git 追踪 ✅】         │
│                                                   │
│  改网站外观                                       │
│  → root/scripts/templates/ 【Git 追踪 ✅】         │
│                                                   │
│  改 Nginx 服务器配置                              │
│  → etc/nginx/              【Git 追踪 ✅】         │
│                                                   │
│  改资源内容                                       │
│  → root/scripts/pantools_export.xlsx 【本地】     │
│                                                   │
│  ❌ 别改这里（自动生成 / 不追踪）                  │
│  → var/www/site/web/                             │
│  → root/scripts/database.db                       │
│  → root/scripts/.env                              │
│                                                   │
└───────────────────────────────────────────────────┘
```

---

## 🔧 常见问题 5 秒定位

| 症状 | 最可能原因 | 速修 |
|------|-----------|------|
| 网站打不开，Cloudflare 522 | Hetzner 云防火墙 | [Hetzner 控制台](https://console.hetzner.cloud) → Firewalls → 加 TCP 80/443 |
| 网站 403 | Nginx 权限问题 | VPS 跑 `cd /root/bigprc-deploy && bash deploy.sh` |
| 改完页面没变化 | 没跑 deploy.sh | VPS 跑 deploy.sh |
| 新增资源没显示 | 没跑 auto_generate.py | VPS 跑 `python3 /root/scripts/auto_generate.py` |
| 本地 preview 报错 | 没装环境 / 没生成网站 | 先跑 `setup.ps1`，再跑 `auto_generate.py` |
| push 报认证错误 | GitHub token 过期 | 去 GitHub → Settings → Developer settings → Personal access tokens 换新的 |
| 部署后网站异常 | 配置/代码有问题 | VPS 跑 `bash deploy.sh rollback` 回滚到上一个版本 |
| 回滚多版本 | 需回到更早的版本 | VPS 跑 `bash deploy.sh rollback 3`（数字代表回退几个提交） |

---

## 🖥️ 服务器信息

| 项目 | 值 |
|------|-----|
| 提供商 | Hetzner |
| 主机名 | ubuntu-4gb-hel1-17 |
| 公网 IP | `37.27.246.3` |
| SSH 端口 | `2222`（不是默认的 22） |
| 仓库路径 | `/root/bigprc-deploy` |
| 网站目录 | `/var/www/site/web` |

### SSH 登录

```bash
ssh -p 2222 root@37.27.246.3
```

> ⚠️ SSH 端口是 **2222**，不是默认的 22。Hetzner 云防火墙也只放行了 2222。

### 紧急回滚

```bash
ssh -p 2222 root@37.27.246.3
cd /root/bigprc-deploy
bash deploy.sh rollback     # 回滚到上一个版本
bash deploy.sh rollback 3   # 回滚 3 个版本
# 会自动显示最近提交记录，回滚后重新部署并重载 Nginx
```

---

## 📚 详细文档

需要更深入的信息（脚本参数、模板变量、部署原理等），请查阅：

👉 **[DEVELOPER_MANUAL.md](DEVELOPER_MANUAL.md)**

---

> 📝 文档最后更新：2026-06-21  
> 🤖 由 Claude Code 根据实战排查经验整理

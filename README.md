# BigPRC — 极客资源技术索引引擎

> 站点: <https://www.bigprc.com>  
> 仓库: <https://github.com/chiangprc/bigprc-deploy>  
> 架构: Python/Jinja2 静态站点生成 + Nginx + Cloudflare  
> 设计: Swiss 国际主义扁平风格 · 纯文字界面 · 暗色模式

BigPRC 是一个**不存储任何文件的资源索引引擎**。它从 Excel 数据源读取第三方网盘分享链接，通过 Python 脚本自动生成全站静态 HTML，部署到 Ubuntu VPS + Nginx 对外服务。全站约 1,267 条资源，覆盖软件工具、学习资料、影音娱乐等领域。

---

## 文档导航

| 文档 | 用途 | 读者 |
|------|------|------|
| **[README.md](README.md)**（本文件） | 项目索引：架构总览、文档导航、快速上手 | 所有人 |
| **[DEVELOPER_MANUAL.md](DEVELOPER_MANUAL.md)**（开发者手册） | 完整系统架构和配置参考。涵盖数据流、目录结构、环境搭建、脚本说明、Nginx 配置、部署流程、模板系统、运维自动化、故障排查 | 开发者 |
| **[WORKFLOW_DAILY.md](WORKFLOW_DAILY.md)**（日常工作流） | 日常运维速查：一分钟命令、文件地图、常见问题 5 秒修复、服务器连接 | 日常运维 |
| **[docs/EVALUATION_AND_IMPROVEMENT_PLAN.md](docs/EVALUATION_AND_IMPROVEMENT_PLAN.md)**（评估与改进方案） | 全站 26 项评估清单及三阶段改进路线图 | 产品/开发 |
| **[docs/DESIGN_SPEC_FLAT_REDESIGN.md](docs/DESIGN_SPEC_FLAT_REDESIGN.md)**（设计规范） | Swiss 扁平化重设计完整规范，含 19 项专家评审意见 | 设计/开发 |
| **[docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)**（项目结构手册） | 全部 60+ 文件的用途说明 | 开发者 |

---

## 核心技术栈

| 层 | 技术 | 用途 |
|---|------|------|
| 数据源 | Excel (.xlsx) | 资源主数据 |
| 中间存储 | SQLite | 数据清洗与查询 |
| 渲染引擎 | Python 3.12 + Jinja2 | 静态 HTML 批量生成 |
| AI 辅助 | OpenAI 兼容 API | SEO 描述自动生成 |
| Web 服务器 | Nginx + Ubuntu | 静态文件服务 + 反向代理 |
| CDN/防护 | Cloudflare | DDoS 防护 + CDN 加速 |
| 监控 | Microsoft Clarity + UptimeRobot | 用户行为分析 + 可用性告警 |
| 版本控制 | Git + GitHub | 配置与脚本管理 |

---

## 页面路由

| URL | 内容 | 实现 |
|-----|------|------|
| `/` | 搜索型首页 | index.html（手工维护） |
| `/list.html` | 资源列表（隐藏入口） | Jinja2 生成 + fetch /index.json |
| `/go/{id}` | 资源详情页 | Nginx rewrite → /static/page/{id}.html |
| `/jump/{id}` | 跳转中转页 | Nginx include jump_rules.conf → 302 |
| `/tools/claudeek.html` | Claudeek 产品页 | 手工静态页面 |
| `/opensearch.xml` | 浏览器地址栏搜索 | 静态 XML |
| `/sitemap.xml` | 搜索引擎地图 | auto_generate.py 生成 |
| `/404.html` | 自定义 404 | 手工静态页面 |

---

## 快速命令

**本地开发**：
```powershell
python root\scripts\auto_generate.py    # 生成全站页面
python local_server.py 8765             # 启动本地预览
```

**推送到生产**：
```powershell
git add -A && git commit -m "..." && git push origin main
```

**VPS 部署**：
```bash
ssh -p 2222 root@37.27.246.3
cd /root/bigprc-deploy && bash deploy.sh && cd /root/scripts && python3 auto_generate.py
```

**紧急回滚**：
```bash
cd /root/bigprc-deploy && bash deploy.sh rollback
```

# BigPRC 全站评估与改进方案

> **评估日期**: 2026-06-22  
> **评估范围**: www.bigprc.com 全站（架构/安全/性能/SEO/用户体验/运维）  
> **评估方法**: 基于源码审查 + Nginx 配置审查 + 模板审查 + 行业最佳实践对标  
> **总条目数**: 26 项（12 项用户体验 + 14 项工程/安全/运维补充）

---

## 目录

- [综述与总体评分](#综述与总体评分)
- [第 1 章：核心体验](#第-1-章核心体验)
- [第 2 章：动静分离与性能](#第-2-章动静分离与性能)
- [第 3 章：安全防护](#第-3-章安全防护)
- [第 4 章：SEO 与内容发现](#第-4-章seo-与内容发现)
- [第 5 章：链接保护与防盗链](#第-5-章链接保护与防盗链)
- [第 6 章：数据分析与用户洞察](#第-6-章数据分析与用户洞察)
- [第 7 章：UI/UX 交互设计](#第-7-章uiux-交互设计)
- [第 8 章：运维与监控](#第-8-章运维与监控)
- [第 9 章：内容与合规](#第-9-章内容与合规)
- [优先级矩阵与实施路线图](#优先级矩阵与实施路线图)

---

## 综述与总体评分

### 项目现状

BigPRC 是一个**纯静态资源索引站**，技术栈为 Excel → SQLite → Python/Jinja2 → Nginx + Cloudflare。全站约 1,267 条资源，不托管实际文件，仅索引第三方网盘分享链接。

**架构评分**：当前架构在"简洁性"维度得分很高——无后端、无数据库查询、无用户系统，天然安全且高性能。但在"用户体验打磨"、"安全防护深度"、"运维自动化"三个维度存在较大改进空间。

| 维度 | 当前得分 | 目标得分 | 涉及条目 |
|------|---------|---------|---------|
| 核心体验 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 条目 1, 7, 8, 9, 10, 11, 12 |
| 性能与缓存 | ⭐⭐ | ⭐⭐⭐⭐⭐ | 条目 2, 16, 17, 18 |
| 安全防护 | ⭐⭐ | ⭐⭐⭐⭐ | 条目 3, 5, 13, 14 |
| SEO | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 条目 4, 24, 25 |
| 数据分析 | ⭐⭐ | ⭐⭐⭐⭐ | 条目 6, 22, 23 |
| 运维可靠性 | ⭐⭐ | ⭐⭐⭐⭐ | 条目 15, 19, 20, 21 |
| 内容合规 | ⭐ | ⭐⭐⭐ | 条目 26 |

---

## 第 1 章：核心体验

### 条目 1：用户能否在 3 秒内进入网站，并通过搜索/分类在 3 次点击内看到目标资源？

**当前状态**：部分达标，有改进空间。

| 环节 | 现状 | 评估 |
|------|------|------|
| 首屏加载 | 首页 `index.html` 仅 ~4KB，无外部 CSS/JS，首次内容绘制 (FCP) < 500ms | ✅ 已达标 |
| 到达列表页 | 首页 → 点击卡片 → `/list.html` (1 次点击) | ✅ 已达标 |
| 列表页加载 | `list.html` 445KB（含全部 1,267 条资源的 HTML），首次加载需传输完整页面 | ⚠️ 偏慢 |
| 搜索体验 | 客户端实时过滤（`filterTable()`），无网络请求 | ✅ 快 |
| 到达详情页 | 列表 → 点击资源名 → `/go/p001` (第 2 次点击) | ✅ 已达标 |
| 获取资源 | 详情页 → 点击下载按钮 → 中转页 5 秒倒计时 → 跳到网盘 (3 次点击 + 5 秒等待) | ⚠️ 3 次点击，但有等待 |

**问题分析**：
1. `list.html` 445KB 对移动网络用户偏大（1,267 行全部渲染在 HTML 中）
2. 中转页的 5 秒倒计时是刻意设计（防刷/广告展示），但用户感知为"等待"而非"安全验证"
3. 缺少资源分类/标签筛选，用户只能靠关键词搜索，浏览体验受限

**改进方案**：

**方案 A：列表页分页改为服务端分页（推荐）**
- 将 `auto_generate.py` 改为生成多个分页文件（`list_1.html`, `list_2.html`...），每页 50-100 条
- 修改 `list.html` 模板，搜索过滤改为异步加载（超出当前页时 fetch 下一页）
- 预计首屏 HTML 从 445KB 降至 ~30KB
- 实施难度：中等（需改 Python 生成逻辑 + 模板 JS）

**方案 B：引入标签/分类系统**
- 在 Excel 数据源中新增"分类"列（如：影视/软件/教程/电子书/其他）
- `auto_generate.py` 为每个分类生成独立列表页（`tag_movie.html`, `tag_software.html`...）
- 首页卡片增加分类入口
- 实施难度：低（仅需 Excel + 模板改动）

**方案 C：中转页倒计时改为"点击即跳"（激进方案）**
- 将 `transit.html` 的 5 秒强制等待改为"立即跳转 + 显示广告横幅"
- 但会损失广告展示时间，需权衡商业模型
- 实施难度：低（改模板）

**推荐实施**：先做方案 B（分类系统），再做方案 A（服务端分页）。方案 C 取决于商业化策略。

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🔴 高 | 中 | 4-6h（方案 A+B） |

---

### 条目 7：真正的"下载/获取"按钮是否为全屏第一视觉焦点，且能与广告明显区分？

**当前状态**：存在明显问题。

当前详情页 `detail.html` 的下载按钮设计：
```css
.btn-main { 
    display: inline-block; 
    background: #1a365d;  /* 深蓝灰——与整体配色一致，视觉上"淹没"在页面中 */
    color: #fff !important; 
    padding: 14px 28px; 
    font-size: 15px; 
    font-weight: bold; 
    border-radius: 2px;   /* 近乎直角，缺少 CTA 感 */
}
```

**问题分析**：
1. 按钮颜色 `#1a365d` 是页面主色调，非 CTA 标准色（应为高对比度亮色，如 `#e74c3c` 或 `#ff6b35`）
2. 详情页布局是**文字优先**（标题 → 描述 → 大小 → 按钮），按钮不在首屏视觉中心
3. 中转页（`transit.html`）的"验证完毕，点击进入网盘"按钮默认隐藏，倒计时结束后才显示，此时用户可能在浏览其他内容
4. 无广告-内容区分需求（目前全站无广告），但若将来增加广告需预留区分机制

**改进方案**：

1. **下载按钮视觉重构**：
   - 主按钮改用高对比度强调色（`#ff6b35` 橘色 或 `#e74c3c` 红色）
   - 增大尺寸至 `padding: 18px 40px; font-size: 17px; border-radius: 8px`
   - 增加 `box-shadow: 0 4px 15px rgba(230, 76, 60, 0.3)` 形成悬浮感
   - 添加微动画（hover 时 `transform: scale(1.03)`）

2. **详情页布局调整**：
   - 将下载按钮移至首屏顶部，在标题下方直接展示
   - 信息层级改为：标题 → 下载按钮 → 大小/格式 → SEO 描述
   - 移动端固定底部悬浮下载按钮

3. **中转页按钮优化**：
   - 按钮始终可见（默认置灰 + 倒计时数字在按钮内或旁边）
   - 倒计时结束后按钮亮起、振动/脉冲动画

**模板改动（`detail.html`）**：

```css
.btn-main { 
    display: inline-block; 
    background: linear-gradient(135deg, #ff6b35, #e74c3c);
    color: #fff !important; 
    padding: 18px 40px; 
    font-size: 17px; 
    font-weight: bold; 
    border-radius: 8px; 
    box-shadow: 0 4px 15px rgba(231, 76, 60, 0.35);
    transition: all 0.2s;
}
.btn-main:hover { 
    transform: scale(1.03); 
    box-shadow: 0 6px 20px rgba(231, 76, 60, 0.5); 
}
```

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🔴 高 | 低 | 1-2h |

---

### 条目 8：资源详情页的首屏是否包含了名称、大小、版本、预览图等最核心的决策信息？

**当前状态**：信息不足，缺少关键决策信息。

当前详情页首屏信息（按出现顺序）：
1. 资源名称（`<h1>` 标题）
2. SEO 描述文案（大段 HTML 文本）
3. 文件大小
4. 下载按钮

**缺失的关键决策信息**：
- ❌ 无资源类型/格式（是压缩包？安装程序？视频？PDF？）
- ❌ 无版本号/更新日期
- ❌ 无预览截图
- ❌ 无下载次数/热度（全静态站点，无可动态查询的数据库）
- ❌ 无文件数量（如压缩包内含几个文件）
- ❌ 无解压密码提示（是否需要密码？密码是什么？）
- ❌ 无适用平台（Windows/Mac/Linux/全平台）

**改进方案**：

**方案 A：扩展 Excel 数据列（推荐）**
- 在 `pantools_export.xlsx` 新增列：`分类`、`版本`、`平台`、`格式`、`更新日期`、`解压密码`
- 修改 `pantools_sync.py` 的数据库表结构，新增对应字段
- 修改 `detail.html` 模板，以信息卡片形式展示

**方案 B：详情页信息架构重构**
```
┌──────────────────────────────────────┐
│  [资源名称]                     ← H1 │
│  ┌──────────────────────────────────┐│
│  │ 📦 格式: RAR  │ 💻 平台: Win   ││
│  │ 📏 大小: 2.3GB│ 📅 更新: 2026-06││
│  │ 🔑 密码: 无   │ 🔥 热度: ★★★★ ││
│  └──────────────────────────────────┘│
│  [======== 获取资源 ========]  ← CTA │
│  ────────────────────────────────── │
│  [SEO 描述内容...]                   │
│  [相关推荐]                          │
└──────────────────────────────────────┘
```

**方案 C：静态"热度"指标**
- 由于是纯静态站点，无法记录真实下载量
- 可用人工编辑的"推荐星级"（1-5 星）代替
- 或根据资源在列表页的排列位置暗示热度

**推荐实施**：方案 A（扩展 Excel）+ 方案 B（信息架构重构）。方案 C 可选。

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🔴 高 | 中 | 3-4h |

---

### 条目 9：在搜索、翻页、等待下载倒计时中，是否有清晰的骨架屏、进度条或状态提示？

**当前状态**：基础可用，但缺乏现代化反馈。

| 场景 | 现状 | 评估 |
|------|------|------|
| 搜索 | 输入即过滤（客户端），无 loading 态——因为是纯客户端过滤，本身不需反馈 | ✅ 合理 |
| 翻页 | `displayTable()` 直接切换显示/隐藏，无过渡动画 | ⚠️ 可优化 |
| 中转倒计时 | 旋转 spinner + 数字倒计时 + 文字说明 | ✅ 基本可用 |
| 页面加载 | HTML 渲染即完成，无异步请求，无骨架屏需求 | ✅ 合理 |
| 搜索无结果 | **无任何提示**——表格直接变空，用户不知道是"无匹配"还是"加载失败" | ❌ 缺失 |

**改进方案**：

1. **搜索无结果状态**：
```javascript
function filterTable() {
    var filter = document.getElementById("searchInput").value.toLowerCase();
    var hasResult = false;
    // ...过滤逻辑...
    if (!hasResult && filter !== "") {
        // 显示"未找到匹配资源"提示
        showNoResult(filter);
    }
}
```
在列表页 `<tbody>` 下方添加 `<tr id="noResultRow" style="display:none"><td colspan="3">未找到包含"xxx"的资源</td></tr>`

2. **翻页过渡动画**：
   - 添加 CSS `transition: opacity 0.2s` 到表格行
   - `displayTable()` 切换时加入短暂 fade 效果

3. **中转页进度增强**：
   - 将数字倒计时改为进度条 + 百分比
   - 添加文字变化动画（"正在验证..." → "即将跳转..."）

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🟡 中 | 低 | 1-2h |

---

### 条目 10：当出现"链接失效/积分不足/权限不够"时，交互是否提供了明确的解决方案引导？

**当前状态**：严重缺失。目前没有任何错误/异常状态的引导。

**现有异常场景**：
1. 网盘链接失效 → 用户点击中转后跳转到第三方网盘，发现"分享已取消"——BigPRC 毫不知情
2. 资源无下载链接 → 详情页只显示一条链接或无按钮，没有任何解释
3. 页面 404 → Nginx 回退到 `index.html`（SPA 模式），用户迷惑

**当前唯一错误处理**：
- `list.html` 空数据：数据库为空时 `auto_generate.py` 打印错误并退出
- Nginx 404：`try_files $uri $uri/ /index.html`（回退到首页，非标准 404 页）
- 中转页无跳转链接：不会出现（生成时已校验）

**改进方案**：

**1. 定制 404 页面**
创建 `root/custom-pages/404.html`：
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>404 - 页面未找到 | BigPRC</title>
</head>
<body>
    <h1>🚫 资源未找到</h1>
    <p>该页面可能已被移除或链接有误</p>
    <ul>
        <li><a href="/list.html">浏览全部资源</a></li>
        <li><a href="/">返回首页</a></li>
    </ul>
</body>
</html>
```

在 Nginx 中配置：
```nginx
error_page 404 /404.html;
location = /404.html {
    root /var/www/site/web;
    internal;
}
```

**2. 死链反馈入口**
在详情页和中转页添加"报告失效"链接：
```html
<a href="mailto:admin@bigprc.com?subject=链接失效报告 - {{ res_id }}">
    ⚠️ 报告此资源已失效
</a>
```

**3. 详情页空链接状态处理**
模板中已有条件判断（`{% if short_url %}...{% elif normal_url %}...{% endif %}`），但缺少"两个链接都没有"的状态。建议增加：
```jinja2
{% if not short_url and not normal_url %}
<div class="no-link-box">
    <p>⚠️ 该资源链接暂未收录，正在更新中</p>
    <a href="mailto:{{ admin_email }}">联系我们获取</a>
</div>
{% endif %}
```

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🔴 高 | 低 | 2-3h |

---

### 条目 11：手机端访问时，各资源卡片和按钮的触控间距是否合规，有无严重的误触广告风险？

**当前状态**：基础可用，但未针对移动端优化触控。

**现状分析**：
- 列表页 `<td>` 中的"获取"链接：`font-weight: bold`，无最小触控区域
- 列表页分页按钮：`padding: 6px 12px`，约 28px 高度——低于推荐的 44px 最小触控区域（Apple HIG）和 48px（Material Design）
- 详情页下载按钮：`padding: 14px 28px`，约 44px 高度——刚好达标
- `viewport` meta 标签已设置 `width=device-width, initial-scale=1.0` ✅
- 表格在小屏幕（320px）会水平溢出——`min-width: 320px` 只能保证不塌陷，但不能保证不横向滚动

**改进方案**：

**1. 移动端列表页重构（推荐）**
- 将 `<table>` 布局改为卡片列表（仅在小屏幕触发）
- 或至少将表格 `min-width` 降至 `280px` + 减小字体

```css
@media (max-width: 600px) {
    table { font-size: 12px; min-width: 280px; }
    th, td { padding: 8px 3px; }
    .page-btn { padding: 10px 14px; font-size: 14px; min-height: 44px; }
    .jump-input { height: 40px; min-width: 50px; }
}
```

**2. 触控区域扩大**
```css
td a { 
    display: inline-block; 
    padding: 8px 12px; 
    min-width: 44px; 
    min-height: 44px; 
    line-height: 28px; 
}
```

**3. 防误触**
- 分页按钮之间增加 `margin: 0 4px`（当前为 3px，略小）
- "跳转"按钮与输入框之间确保足够间距

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🟡 中 | 低 | 1-2h |

---

### 条目 12：解压密码、提取码等关键字段是否配备了"一键复制"的微交互按钮？

**当前状态**：完全不适用（Pass）。

BigPRC 是资源索引站，不直接提供下载链接，也没有密码/提取码字段。所有资源通过中转页跳转到第三方网盘，解压密码在网盘页面内提供（如果有的话）。

**适用性判断**：此条目在当前业务模型下不适用。但如果未来扩展以下场景，则需要：
- 直接在详情页展示网盘提取码
- 直接展示磁力链接/ed2k 链接
- 展示解压密码

**预留设计**：
```html
<span class="copy-field">
    提取码: <code>abc123</code>
    <button onclick="navigator.clipboard.writeText('abc123')" class="copy-btn">
        📋 复制
    </button>
</span>
```

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| ⚪ 暂不适用 | - | - |

---

## 第 2 章：动静分离与性能

### 条目 2：所有的图片、zip/pdf 等大文件是否已经剥离出源站服务器，走独立 CDN/存储？

**当前状态**：天然满足。

BigPRC **不托管任何实际文件**。所有资源均为第三方网盘链接。站点本身仅包含 HTML 文件，无图片、视频、PDF、zip 等大文件。

**唯一需要关注的点**：
- 网站图标（favicon）：当前未配置，可上传到 Cloudflare 并使用 CDN 分发
- 中转页若将来需要展示广告横幅图片，应使用独立图床/CDN，不得放在 VPS 上
- 详情页的预览截图（若条目 8 方案实施）应使用外部图床 URL

**改进方案**：
1. 添加 favicon：生成后通过 Cloudflare CDN 分发
2. 文档化要求：所有媒体资源使用外部 URL（图床/CDN），禁止放入 VPS

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🟢 低 | 低 | 0.5h |

---

### 条目 16：浏览器缓存策略——Nginx 对静态资源是否配置了 Cache-Control / Expires 头？

**当前状态**：完全未配置。

当前 Nginx 主站配置（`etc/nginx/sites-available/default`）没有任何 `Cache-Control`、`Expires`、`ETag` 设置。`nginx.conf` 中也未配置。

**影响**：
- 浏览器每次访问都请求完整 HTML（虽有 gzip 压缩，但无协商缓存）
- 列表页 445KB × 重复访问 = 大量不必要流量
- `Cloudflare → 源站` 回源率 100%（CDN 不知道哪些可以缓存）

**改进方案**：

在 Nginx `default` 配置中添加：

```nginx
# HTML 页面：短期缓存 + 协商缓存
location ~* \.html$ {
    add_header Cache-Control "public, max-age=300, must-revalidate";
    add_header Vary "Accept-Encoding";
    etag on;
}

# 静态资源（如有）：长期缓存
location ~* \.(css|js|svg|png|jpg|jpeg|gif|ico|woff2?)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# 资源详情页：中等缓存
location /static/page/ {
    add_header Cache-Control "public, max-age=3600, must-revalidate";
    etag on;
}

# sitemap：短期缓存
location = /sitemap.xml {
    add_header Cache-Control "public, max-age=3600";
}
```

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🔴 高 | 低 | 0.5h |

---

### 条目 17：Cloudflare 缓存规则——是否针对不同 URL 配置了不同缓存层级？

**当前状态**：未配置（使用 Cloudflare 默认策略）。

Cloudflare 默认对 HTML 不缓存，对静态资源缓存。但未针对 BigPRC 的 URL 结构做精细化配置。

**改进方案**：

在 Cloudflare Dashboard → Rules → Page Rules 中配置：

| URL 模式 | 缓存级别 | 边缘缓存 TTL | 说明 |
|---------|---------|-------------|------|
| `www.bigprc.com/static/page/*.html` | Cache Everything | 2 hours | 资源详情页变化不频繁 |
| `www.bigprc.com/list.html` | Cache Everything | 30 minutes | 列表页需更频繁更新 |
| `www.bigprc.com/sitemap.xml` | Cache Everything | 1 hour | 搜索引擎地图 |
| `www.bigprc.com/go/*` | No Cache (Bypass) | - | 确保走 Nginx rewrite |
| `www.bigprc.com/jump/*` | No Cache (Bypass) | - | 确保走 Nginx redirect |

另外启用 Cloudflare 的 Auto Minify（HTML/CSS/JS）和 Brotli 压缩（比 gzip 小 15-20%）。

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🟡 中 | 低 | 1h |

---

### 条目 18：列表页首屏的关键 CSS 是否内联以避免额外网络往返？

**当前状态**：已部分满足。

当前架构下，所有 CSS 都是内联的（`<style>` 标签在 `<head>` 中），没有外部 CSS 文件。这是好事——无需额外网络请求。

**但存在的问题**：
- 列表页（`list.html`）所有 CSS 都在 `<head>` 中，但模板继承自 `layout.html`，合起来约 200 行 CSS
- 对于 445KB 的列表页，CSS 占比不到 2KB，不是瓶颈
- 真正的瓶颈是 1,267 行 `<tr>` 数据全部在 HTML 中

**改进方案**：
- 如果条目 1 的"服务端分页"方案实施，列表页首屏 HTML 将降至 ~30KB，CSS 内联策略完全足够
- 无需额外动作

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🟢 低（依赖条目 1） | - | - |

---

## 第 3 章：安全防护

### 条目 3：Nginx 或 CDN 层面对下载/API 接口是否配置了严格的 Rate Limit？

**当前状态**：完全未配置。

当前 Nginx 配置中**没有任何 `limit_req` 或 `limit_conn` 指令**。`nginx.conf` 中也未配置。

**风险分析**：
- `/go/*`（资源详情页）：无限制，可被爬虫全量抓取
- `/jump/*`（跳转中转）：无限制，可被用于 SSRF 跳板
- `/ws`（WebSocket）：无限制，可被频繁连接轰炸 OpenClaw
- 全站无 WAF 规则

**改进方案**：

**1. Nginx 层 Rate Limit**

在 `nginx.conf` 的 `http` 块中添加：
```nginx
# 定义限流区域
limit_req_zone $binary_remote_addr zone=resource:10m rate=30r/m;
limit_req_zone $binary_remote_addr zone=jump:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=general:10m rate=60r/m;

# 定义连接限制
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;
```

在 `sites-available/default` 的对应 location 中：
```nginx
# 资源页面：每分钟 30 次请求
location /go/ {
    limit_req zone=resource burst=10 nodelay;
    try_files $uri $uri/ @rewrite_go;
}

# 跳转接口：每分钟 10 次请求（防止滥用）
location /jump/ {
    limit_req zone=jump burst=3 nodelay;
    include /etc/nginx/snippets/jump_rules.conf;
    return 302 https://www.bigprc.com;
}

# WebSocket：连接数限制
location = /ws {
    limit_conn conn_limit 5;
    proxy_pass http://127.0.0.1:18789;
    # ...
}

# 全局限流
location / {
    limit_req zone=general burst=20 nodelay;
    try_files $uri $uri/ /index.html;
}
```

**2. Cloudflare 层补充**
- 启用 Cloudflare Rate Limiting（免费套餐 1 条规则）
- 配置规则：`/jump/*` 路径 10 次/分钟/IP
- 启用 Bot Fight Mode（自动拦截确认的爬虫）

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🔴 高 | 中 | 2-3h |

---

### 条目 13：资源链接有效性监控——是否有自动化脚本定期检测死链并告警？

**当前状态**：完全缺失。

这是 BigPRC **最关键的运维盲区**。作为纯索引站，链接有效就是产品的生命线。1,267 条资源中，第三方网盘链接可能随时失效（分享取消、文件删除、账号被封）。

**影响**：
- 用户点击 → 中转倒计时 → 跳到网盘 → "分享已取消" → 体验极差
- 无任何监控机制，只能依赖用户手动反馈（但当前也没有反馈入口）

**改进方案**：

**创建死链检测脚本 `check_dead_links.py`**：

```python
import sqlite3
import requests
import time
from datetime import datetime

# 网盘链接存活特征码
DEAD_PATTERNS = [
    "分享已取消", "文件已删除", "链接不存在", "页面不存在",
    "已失效", "该分享已被取消", "你来晚了", "已被删除",
    "404", "已过期", "已下架", "链接失效"
]

ALIVE_PATTERNS = [
    "pan.baidu.com", "quark.cn", "alipan.com",  # 网盘页面正常特征
    "请输入提取码", "文件大小", "下载"
]

def check_link(url, res_id):
    """检测单个链接是否存活"""
    try:
        r = requests.head(url, timeout=15, allow_redirects=True)
        if r.status_code == 200:
            return "alive"
        # 进一步 GET 检查
        r = requests.get(url, timeout=15, stream=True)
        content = r.text[:2000]
        for pattern in DEAD_PATTERNS:
            if pattern in content:
                return "dead"
        for pattern in ALIVE_PATTERNS:
            if pattern in content:
                return "alive"
        return "uncertain"
    except Exception as e:
        return f"error: {e}"

# 批量检测（每次检测 50 条，避免被对方限流）
def batch_check():
    conn = sqlite3.connect("database.db")
    resources = conn.execute("SELECT res_id, normal_url, short_url FROM resources").fetchall()
    
    dead_links = []
    for i, (res_id, normal_url, short_url) in enumerate(resources):
        for url in [normal_url, short_url]:
            if not url:
                continue
            status = check_link(url, res_id) 
            if status == "dead":
                dead_links.append((res_id, url))
            time.sleep(2)  # 间隔 2 秒，避免被封
        
        if (i + 1) % 10 == 0:
            print(f"进度: {i+1}/{len(resources)}")
    
    # 输出结果
    if dead_links:
        print(f"\n⚠️ 发现 {len(dead_links)} 条死链:")
        for res_id, url in dead_links:
            print(f"  {res_id}: {url}")
    return dead_links
```

**部署方式**：
- VPS crontab：`0 3 * * 1 cd /root/scripts && python3 check_dead_links.py > /root/dead_links_report.txt`
- 每周一凌晨 3 点检测一次
- 报告邮件通知管理员

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🔴 高 | 中 | 3-4h |

---

### 条目 14：内容安全策略 (CSP)——静态页面是否配置了 CSP 头？

**当前状态**：完全未配置。

无 CSP / X-Frame-Options / X-Content-Type-Options 等安全头。

**风险分析**：
- 资源详情页的 AI 生成 HTML 内容（`seo_desc|safe`）未经过滤直接渲染——若 AI 生成内容中包含恶意脚本，存在 XSS 风险
- 无 `X-Frame-Options`：可被其他网站 `<iframe>` 嵌入钓鱼
- 无 `X-Content-Type-Options: nosniff`：MIME 嗅探风险

**改进方案**：

在 Nginx `default` server block 中添加安全头：

```nginx
# 安全头
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# CSP：限制脚本来源和内联样式
add_header Content-Security-Policy "
    default-src 'self';
    script-src 'self' 'unsafe-inline' https://www.clarity.ms;
    style-src 'self' 'unsafe-inline';
    img-src 'self' data: https:;
    connect-src 'self' https://www.clarity.ms;
    frame-ancestors 'self';
    base-uri 'self';
    form-action 'self';
" always;
```

> ⚠️ `'unsafe-inline'` 是因为当前所有 CSS/JS 都是内联的（`<style>` + `<script>` 标签）。理想情况下应改为外部文件 + nonce/hash，但考虑到项目简洁性，暂时保留内联。

**模板层额外防护**：
- 在 `auto_generate.py` 渲染 SEO 描述前，增加 HTML 安全过滤
```python
import html

# 在 render_single_page 之前
res['seo_desc'] = html.escape(res.get('seo_desc', ''))
# 或保留允许的安全标签
from bleach import clean
res['seo_desc'] = clean(res['seo_desc'], tags=['p', 'br', 'strong', 'em', 'a'], attributes={'a': ['href']})
```

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🔴 高 | 低 | 1-2h |

---

### 条目 5：对外分享的下载链接是否带有 TTL 签名，防止被其他网站直接盗链？

**当前状态**：完全不适用（设计上天然免疫）。

BigPRC 的跳转链路是：
```
用户 → /jump/p001 → Nginx 302 redirect → https://pan.baidu.com/s/xxxxx
```

跳转目标（`pan.baidu.com/s/xxxxx`）是百度自身的分享链接，百度自己控制失效和访问权限。BigPRC 无法也不需要对百度链接再包一层签名。

**唯一可做的防盗链措施**：
- 在 `/jump/*` 路径增加 Referer 检查（防止其他网站直接使用 BigPRC 的跳转链）
- TTL 签名对于纯静态站点实现成本极高（需要动态签名服务 + 时间戳校验）

**改进方案**（轻量级 Referer 检查）：

```nginx
location /jump/ {
    # 阻止空 Referer 和外部 Referer
    if ($http_referer !~* "^https?://(www\.)?bigprc\.com") {
        return 403;
    }
    include /etc/nginx/snippets/jump_rules.conf;
    return 302 https://www.bigprc.com;
}
```

> ⚠️ Referer 检查可以被伪造，属于轻量级防护。完整 TTL 签名需要动态后端服务，与当前静态架构冲突。

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🟡 中 | 低 | 0.5h |

---

## 第 4 章：SEO 与内容发现

### 条目 4：每一个资源详情页是否都有唯一的 Canonical 标签，且去除了筛选参数带来的死循环？

**当前状态**：已实现，但存在遗漏。

**已有 Canonical 支持**：
- `layout.html` 模板中有：`{% if canonical_url %}<link rel="canonical" href="{{ canonical_url }}">{% endif %}`
- `auto_generate.py` 传入：`canonical_url=f"{DOMAIN}/go/{res['res_id']}"`
- 中转页模板（`transit.html`）**未传入 canonical_url**——因为模板继承的是 `layout.html` 但未设置 `canonical_url` 变量

**问题**：
1. 中转页缺少 canonical 标签（搜索引擎可能索引 `_transit.html` 和 `_short_transit.html` 页面）
2. 列表页的 canonical 已设置（`list.html` 在 `layout.html` 中设置了默认值）
3. 无分页参数问题（当前为纯 JS 客户端分页，无 URL 参数，天然无此问题）✅

**改进方案**：

修改 `auto_generate.py`，为中转页也传入 canonical：

```python
# transit.html 渲染时增加 canonical_url
transit_html = transit_template.render(
    title=res['title'], jump_id=res['res_id'],
    admin_email=ADMIN_EMAIL, clarity_id=CLARITY_ID,
    canonical_url=f"{DOMAIN}/go/{res['res_id']}"  # ← 新增：指向详情页而非中转页
)
```

中转页的 canonical 应指向详情页（`/go/p001`），告诉搜索引擎"详情页是原始页面，中转页是附属页"。

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🟡 中 | 低 | 0.5h |

---

### 条目 24：结构化数据 (JSON-LD)——资源详情页是否嵌入了 Schema.org 标记？

**当前状态**：缺失。

当前所有模板和生成脚本中没有任何 JSON-LD 结构化数据。

**改进方案**：

在 `detail.html` 模板中添加 JSON-LD：

```html
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    "name": "{{ title }}",
    "description": "{{ seo_desc|striptags|truncate(200) }}",
    "url": "{{ canonical_url }}",
    "applicationCategory": "UtilitiesApplication",
    "operatingSystem": "Windows, macOS, Linux",
    "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "CNY"
    },
    "fileSize": "{{ size }}"
}
</script>
```

对于不同类型资源，可扩展支持：
- 影视资源 → `@type: Movie` + `duration` / `genre`
- 电子书 → `@type: Book` + `author` / `isbn`
- 软件 → `@type: SoftwareApplication`

需要 Excel 新增 `资源类型` 列来区分。

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🟢 低 | 中 | 2-3h |

---

### 条目 25：Open Graph 标签——分享到微信/QQ/微博时是否有 og 标签？

**当前状态**：缺失。

当前 `layout.html` 中没有任何 OG 标签。

**影响**：
- 微信内分享链接无预览卡片（只有纯文本 URL）
- QQ/微博同理
- 社交媒体分享点击率低

**改进方案**：

在 `layout.html` 的 `<head>` 中添加：

```html
<!-- Open Graph -->
<meta property="og:title" content="{% block og_title %}{{ self.title() }}{% endblock %}">
<meta property="og:description" content="{% block og_description %}BigPRC 极客资源湾 — 无广告纯净资源分享{% endblock %}">
<meta property="og:url" content="{{ canonical_url or 'https://www.bigprc.com' }}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="BigPRC 极客资源湾">
<meta property="og:locale" content="zh_CN">
{% block og_image %}
<meta property="og:image" content="https://www.bigprc.com/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
{% endblock %}

<!-- Twitter Card（同时被部分平台使用） -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{% block twitter_title %}{{ self.title() }}{% endblock %}">
<meta name="twitter:description" content="{% block twitter_description %}BigPRC 极客资源湾 — 无广告纯净资源分享{% endblock %}">
```

同时需要设计一张 1200×630 的 OG 分享图，放在 VPS `/var/www/site/web/og-image.png`。

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🟡 中 | 低 | 1h（含设计 OG 图） |

---

## 第 5 章：链接保护与防盗链

> 条目 5（链接 TTL 签名）已在第 3 章中讨论。

---

## 第 6 章：数据分析与用户洞察

### 条目 6：是否配置了全站热图或点击追踪，明确知道哪类资源点击率最高、哪个下载按钮无人问津？

**当前状态**：Microsoft Clarity 已集成，但未充分利用。

**已有能力**：
- ✅ Microsoft Clarity 已集成（热图 + 会话录制）
- ✅ 代码中 `clarity_id` 变量已传入所有模板

**未利用的能力**：
- ❌ 未配置自定义事件追踪（点击下载按钮、跳转成功等关键行为）
- ❌ 无转化漏斗（首页 → 列表 → 详情 → 跳转）
- ❌ 无资源级热图对比（哪个资源被点最多？）

**改进方案**：

**1. 自定义事件埋点**

在关键交互处添加 Clarity 自定义标签和事件：

```javascript
// 详情页下载按钮点击
document.querySelector('.btn-main').addEventListener('click', function() {
    if (window.clarity) {
        clarity("set", "resource_id", "{{ res_id }}");
        clarity("set", "drive", "{{ drive_name }}");
        clarity("event", "download_click");
    }
});

// 中转页跳转成功
window.addEventListener('beforeunload', function() {
    if (window.clarity) {
        clarity("event", "redirect_success");
    }
});

// 搜索行为
document.getElementById('searchInput').addEventListener('input', function() {
    if (window.clarity) {
        clarity("event", "search", this.value);
    }
});
```

**2. 中转页添加 Google Analytics 事件（可选）**
```html
<!-- 仅在跳转前触发，记录中转成功 -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXX"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('js', new Date());
gtag('config', 'G-XXXXXXXX');
gtag('event', 'redirect', {
    'event_category': 'resource',
    'event_label': '{{ jump_id }}'
});
</script>
```

**3. 月度报告脚本**
```python
# 从 Clarity API 拉取热门资源数据
# 或从 Nginx 访问日志中分析 /jump/* 的访问频率
# 输出 Top 50 点击资源 → Excel 报告
```

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🔴 高 | 中 | 2-3h |

---

### 条目 22：转化漏斗追踪——从「列表页 → 详情页 → 跳转页 → 实际离开」的每一步流失率是否可量化？

**当前状态**：完全缺失。

无任何漏斗追踪机制。无法回答：
- 每天有多少人从列表页进入详情页？
- 详情页的下载按钮点击率（CTR）是多少？
- 中转页的跳转完成率（5 秒倒计时后真正离开）是多少？
- "Claudeek 工具"卡片被点击了多少次？

**改进方案**：

**全静态漏斗追踪**（无需后端）：

利用 URL 参数传递来源信息：

```
列表页 → /go/p001?from=list
首页 → /go/p001?from=index
相关推荐 → /go/p001?from=related
```

在详情页和中转页检测来源参数并记录到 Clarity：
```javascript
var urlParams = new URLSearchParams(window.location.search);
var from = urlParams.get('from');
if (from && window.clarity) {
    clarity("set", "source_page", from);
}
```

在关键页面设置"虚拟页面浏览"事件：
```javascript
// 中转页加载 → 记录为 funnel_step_3
clarity("event", "funnel_step", "transit_page_loaded");

// 5 秒后实际跳转 → 记录为 funnel_step_4 (完成)
clarity("event", "funnel_step", "redirect_success");
```

**漏斗定义**：
```
Step 1: 首页访问 (现有 Clarity)
Step 2: 列表页访问 (现有 Clarity)
Step 3: 详情页访问 → clarity("event", "detail_view", "{{ res_id }}")
Step 4: 点击下载按钮 → clarity("event", "download_click")
Step 5: 中转页加载 → clarity("event", "transit_loaded")
Step 6: 跳转完成 → clarity("event", "redirect_complete")
```

通过 Clarity Dashboard 对比各步骤事件量，计算流失率。

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🔴 高 | 低 | 1-2h |

---

### 条目 23：死链用户反馈入口——当用户遇到失效链接时是否有"举报失效"按钮？

**当前状态**：完全缺失。

（已在条目 10 中详细展开，此处简略）

**改进方案**（同条目 10 第 2 点）：
- 详情页添加"报告失效"mailto 链接
- 中转页添加"链接打不开？"反馈入口
- 长期可改为表单收集（Google Forms / 腾讯问卷）

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🔴 高 | 低 | 0.5h |

---

## 第 7 章：UI/UX 交互设计

> 条目 7-12 已在第 1 章中全部覆盖。

---

## 第 8 章：运维与监控

### 条目 15：备份策略——核心资产是否有定期异地备份？

**当前状态**：存在风险。

**核心资产清单**：
| 资产 | 位置 | 当前备份 | 风险 |
|------|------|---------|------|
| `pantools_export.xlsx` | VPS `/root/scripts/` | GitHub（如果 push 了） | ⚠️ 不确定是否每次编辑后 push |
| `database.db` | VPS `/root/scripts/` | ❌ 无 | 丢失需从 Excel 重建 |
| Nginx 配置 | VPS `/etc/nginx/` | ✅ GitHub（通过 deploy.sh 软链接） | 低 |
| Let's Encrypt 证书 | VPS `/etc/letsencrypt/` | ❌ 无 | 可重新申请 |
| Python 脚本 | VPS `/root/scripts/` | ✅ GitHub | 低 |

**最大风险**：Excel 和 SQLite 数据仅存在 VPS 上，VPS 硬盘故障 = 数据全丢。

**改进方案**：

**1. 自动化备份脚本 `backup.sh`**：
```bash
#!/bin/bash
# VPS 每日备份脚本
BACKUP_DIR="/root/backups"
DATE=$(date +%Y%m%d)
mkdir -p "$BACKUP_DIR"

# 打包核心数据
tar czf "$BACKUP_DIR/bigprc_data_$DATE.tar.gz" \
    /root/scripts/pantools_export.xlsx \
    /root/scripts/database.db \
    /root/scripts/.env \
    /root/bigprc-deploy/

# 保留最近 7 天备份
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete

# 上传到远程存储（示例：rclone to Google Drive）
rclone copy "$BACKUP_DIR/bigprc_data_$DATE.tar.gz" gdrive:/bigprc-backups/
```

**2. crontab 定时任务**：
```
0 2 * * * bash /root/scripts/backup.sh >> /root/backup.log 2>&1
```

**3. Excel 数据 GitHub 自动备份**（推荐）：
- 在 `.gitignore` 中移除 `pantools_export.xlsx` 和 `database.db` 的排除
- 或者创建 `data/` 子目录专门存放数据文件并纳入 Git
- 每次数据变更后 commit + push

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🔴 高 | 中 | 2h |

---

### 条目 19：部署回滚能力——deploy.sh 是否支持一键回滚？

**当前状态**：拥有天然回滚能力，但未文档化。

**现有机制**：
- `deploy.sh` 使用 `git pull` + `ln -sf`（软链接）
- 软链接指向 Git 仓库中的文件
- 通过 `git checkout` 可回滚到任意历史版本
- Nginx 语法检查失败会自动阻止部署

**缺失的回滚 documentation**：

当前 `deploy.sh` 和 `DEVELOPER_MANUAL.md` 中**没有回滚步骤**。

**改进方案**：

**1. 在 `deploy.sh` 中添加回滚功能**：

```bash
# deploy.sh 新增参数
if [ "${1:-}" = "rollback" ]; then
    echo "⏪ 回滚到上一个提交..."
    cd "$DEPLOY_ROOT"
    git checkout HEAD~1
    echo "已回滚到 $(git rev-parse --short HEAD)"
    # 重新软链接并重载
    # ... (执行步骤 2-6)
fi
```

**2. 在 `DEVELOPER_MANUAL.md` 和 `WORKFLOW_DAILY.md` 中添加回滚文档**：

```markdown
### 紧急回滚步骤

# 1. SSH 登录 VPS
ssh -p 2222 root@37.27.246.3

# 2. 进入部署目录
cd /root/bigprc-deploy

# 3. 回滚到上一个版本
git log --oneline -5          # 查看最近提交
git checkout <commit_hash>    # 切到指定版本

# 4. 重新部署
bash deploy.sh

# 5. 验证
curl -I https://www.bigprc.com
```

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🟡 中 | 低 | 1h |

---

### 条目 20：SSL 证书续期告警——Let's Encrypt 证书自动续期失败时是否有通知？

**当前状态**：未配置告警。

Let's Encrypt certbot 通常通过 systemd timer 或 cron 自动续期，但续期失败时：
- ❌ 默认无通知
- ❌ 证书过期后网站 HTTPS 无法访问（浏览器显示安全警告）
- ❌ 用户大量流失

**改进方案**：

**创建证书检查 + 告警脚本 `check_ssl.sh`**：

```bash
#!/bin/bash
# 检查 SSL 证书有效期，不足 14 天时发送告警邮件

DOMAIN="www.bigprc.com"
THRESHOLD=14
CERT_FILE="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
NOW_EPOCH=$(date +%s)
DAYS_LEFT=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))

if [ $DAYS_LEFT -le $THRESHOLD ]; then
    echo "⚠️ SSL 证书将在 $DAYS_LEFT 天后过期！" | \
        mail -s "BigPRC SSL Certificate Expiring Soon" admin@bigprc.com
fi

# 同时检查 certbot timer 状态
if ! systemctl is-active --quiet certbot.timer; then
    echo "❌ certbot.timer 未运行！" | \
        mail -s "BigPRC Certbot Timer Down" admin@bigprc.com
fi
```

**crontab**：
```
0 9 * * * bash /root/scripts/check_ssl.sh
```

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🔴 高 | 低 | 1h |

---

### 条目 21：网站可用性监控——是否接入了外部 uptime 监控？

**当前状态**：完全缺失。

无任何外部监控。VPS 宕机或 Nginx 崩溃 = 无人知晓，直到用户反馈或自己访问发现。

**改进方案**：

**免费监控服务接入**（5 分钟搞定）：

| 服务 | 免费额度 | 用途 |
|------|---------|------|
| [UptimeRobot](https://uptimerobot.com) | 50 个监控 / 5 分钟间隔 | HTTP(s) 可用性 + 关键词匹配 |
| [Better Uptime](https://betterstack.com) | 10 个监控 / 3 分钟间隔 | 更美观的 Dashboard + 电话告警 |
| 百度云观测 | 免费 | 国内线路监控 |

**推荐配置**：
1. 注册 UptimeRobot（免费）
2. 添加监控：
   - `https://www.bigprc.com` — HTTP(s) 监控，关键词 "BigPRC"
   - `https://claw.bigprc.com` — HTTP(s) 监控
3. 配置告警：邮件 → `admin@bigprc.com`
4. 可选：Telegram/Discord/Slack Webhook 通知

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🔴 高 | 极低 | 0.5h |

---

## 第 9 章：内容与合规

### 条目 26：AI 内容合规标识——AI 生成的 SEO 描述是否需要按法规标识？

**当前状态**：未标识。

`ai_seo_writer.py` 生成的 SEO 描述直接嵌入详情页 HTML，没有任何"此内容由 AI 生成"的标识。

**法规背景**：
- 🆕 2025 年 9 月施行的《人工智能生成合成内容标识办法》要求：向公众传播的 AI 生成内容应进行标识
- 执法力度正在逐步加强，尤其对商业网站
- 标识方式可以是显式文本（"本文由 AI 辅助生成"）或元数据标记

**改进方案**：

**1. 模板层添加 AI 标识**（推荐，低风险）

在 `detail.html` 模板中 SEO 描述区域的末尾添加：

```html
<div class="desc-box">
    <strong>[ 资源档案 ]</strong><br>
    {{ seo_desc|safe }}
    {% if seo_desc and seo_desc|length > 100 %}
    <p style="font-size: 11px; color: #999; margin-top: 8px; text-align: right;">
        ⓘ 内容由 AI 辅助生成，仅供参考
    </p>
    {% endif %}
</div>
```

**2. 元数据标记**（可选，更合规）

在 `layout.html` 中添加：
```html
<meta name="ai-generated" content="partial">
<meta name="ai-content-scope" content="seo-description">
```

**3. Excel 中标记 AI 生成条目**

在 `pantools_export.xlsx` 中新增列 `AI生成`（是/否），只有标记为"是"的条目才显示 AI 标识。手工撰写的 SEO 描述无需标识。

**4. `auto_generate.py` 传递标识状态**：
```python
# 从数据库读取 ai_generated 字段
res['ai_generated'] = row.get('ai_generated', False)
# 传入模板
detail_template.render(..., ai_generated=res['ai_generated'])
```

模板中条件渲染：
```jinja2
{% if ai_generated %}
<p class="ai-disclaimer">ⓘ 本描述由 AI 辅助生成</p>
{% endif %}
```

| 优先级 | 难度 | 预估工时 |
|--------|------|---------|
| 🟡 中 | 低 | 1h |

---

## 优先级矩阵与实施路线图

### 优先级矩阵

```
高影响 ┤  条目1(A)  条目6   条目7
       │  条目8     条目10  条目3
       │  条目13    条目14  条目15
       │  条目16    条目20  条目21
       │  条目22
       │
       │  条目9     条目11  条目4
       │  条目17    条目19  条目5
       │  条目24    条目25  条目26
低影响 ┤  条目2     条目12  条目18
       │
       └──────────────────────────
         低成本              高成本
         (配置/模板)         (新脚本/架构改动)
```

### 实施路线图

#### 🚀 第一阶段：紧急修复（本周完成，约 10h）

| 序号 | 条目 | 行动 | 工时 |
|------|------|------|------|
| 1 | 条目 16 | Nginx 缓存策略配置 | 0.5h |
| 2 | 条目 14 | 安全头 (CSP / X-Frame / X-Content-Type) | 1h |
| 3 | 条目 3 | Nginx Rate Limit + Cloudflare Rate Limiting | 2h |
| 4 | 条目 21 | UptimeRobot 监控接入 | 0.5h |
| 5 | 条目 20 | SSL 证书续期告警脚本 | 1h |
| 6 | 条目 15 | 数据备份脚本 + crontab | 2h |
| 7 | 条目 10 | 404 页面 + 死链反馈入口 + 空链接处理 | 2h |
| 8 | 条目 19 | deploy.sh 回滚功能 + 文档 | 1h |

#### 🔧 第二阶段：体验优化（下周完成，约 12h）

| 序号 | 条目 | 行动 | 工时 |
|------|------|------|------|
| 9 | 条目 7 | 下载按钮视觉重构 + 详情页布局调整 | 2h |
| 10 | 条目 8 | Excel 扩展 + 详情页信息架构重构 | 3h |
| 11 | 条目 9 | 搜索无结果状态 + 翻页过渡动画 | 1h |
| 12 | 条目 11 | 移动端适配优化 + 触控区域扩大 | 1h |
| 13 | 条目 4 | 中转页 canonical 修复 | 0.5h |
| 14 | 条目 5 | /jump/* Referer 防盗链检查 | 0.5h |
| 15 | 条目 6 | Clarity 自定义事件埋点（下载/跳转/搜索） | 2h |
| 16 | 条目 22 | 转化漏斗追踪（来源参数 + 虚拟页面浏览） | 1h |
| 17 | 条目 17 | Cloudflare 缓存规则精细化配置 | 1h |

#### 📈 第三阶段：功能增强（两周内完成，约 14h）

| 序号 | 条目 | 行动 | 工时 |
|------|------|------|------|
| 18 | 条目 1A | 列表页服务端分页 | 3h |
| 19 | 条目 1B | 资源分类/标签系统 | 3h |
| 20 | 条目 13 | 死链自动检测脚本 + crontab | 4h |
| 21 | 条目 24 | JSON-LD 结构化数据 | 2h |
| 22 | 条目 25 | Open Graph 标签 + OG 分享图 | 1h |
| 23 | 条目 26 | AI 内容合规标识 | 1h |
| 24 | 条目 2 | favicon 添加 | 0.5h |

### 总工时估算

| 阶段 | 工时 |
|------|------|
| 第一阶段（紧急修复） | ~10h |
| 第二阶段（体验优化） | ~12h |
| 第三阶段（功能增强） | ~14h |
| **合计** | **~36h** |

---

> 📝 本文档基于 2026-06-22 的项目源码状态编写。  
> 如项目架构有重大变更（如引入后端服务、用户系统、支付系统等），部分条目需重新评估。  
> 建议每季度重新 review 本评估清单。

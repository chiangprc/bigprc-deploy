# BigPRC 扁平化重设计规范

> 版本: v2.3 · 2026-06-22  
> 设计方向: Swiss 国际主义扁平风格  
> 核心理念: 无图标、无渐变、无阴影泛滥、文字即界面  
> 无障碍: WCAG AA (正文对比度 ≥ 4.5:1)

---

## 1. 全局设计令牌

```
┌─ 亮色主题 ───────────────────────────┐
│ 背景         #ffffff                   │
│ 前景文字     #1a1a1a                   │
│ 次级文字     #666666  ← WCAG AA 合规   │
│ 边框         #e5e5e5 (1px solid)      │
│ 主色         #1a365d (深蓝，仅链接)     │
│ 强调 CTA     #c0392b (红，实心按钮)     │
│ 卡片底       #fafafa                   │
│ 间距单位     24px / 16px / 8px        │
│ 圆角         4px (输入框、按钮)         │
│ 字体         system-ui, sans-serif    │
│ 触控最小区域 44px × 44px (Apple HIG)   │
└──────────────────────────────────────┘

┌─ 暗色主题 ───────────────────────────┐
│ 背景         #121212                   │
│ 前景文字     #e0e0e0                   │
│ 次级文字     #999999                   │
│ 边框         #2a2a2a                   │
│ 主色         #5c9ce6                   │
│ 强调 CTA     #e74c3c (红，实心按钮)     │
│ 卡片底       #1a1a1a                   │
└──────────────────────────────────────┘
```

### 1a. 全局无障碍：键盘焦点环

```css
/* 仅键盘导航时显示焦点，鼠标/触控用户无感 */
:focus-visible {
    outline: 2px solid var(--primary);
    outline-offset: 2px;
}

/* 纯文字交互元素同样需要 */
a:focus-visible, button:focus-visible, input:focus-visible {
    border-radius: 2px;
}
```

### 1b. 暗色模式防闪烁 (FOUC Prevention)

在 `<head>` 最顶部（`<meta charset>` 之后、任何 CSS/JS 之前）插入阻塞内联脚本：

```html
<script>
(function(){
    var t = localStorage.getItem('theme');
    if (t === 'dark' || (!t && window.matchMedia('(prefers-color-scheme:dark)').matches)) {
        document.documentElement.setAttribute('data-theme', 'dark');
    }
})();
</script>
```

CSS 选择器改用属性而非类名：
```css
body { background: #fff; color: #1a1a1a; }
[data-theme="dark"] body { background: #121212; color: #e0e0e0; }
```

`data-theme` 在 DOM 构建前就设置完毕，浏览器不会先渲染白色再切换到暗色。

### 1c. 滚动条扁平化

```css
/* Webkit (Chrome/Edge/Safari) */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #ccc; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #aaa; }

[data-theme="dark"] ::-webkit-scrollbar-thumb { background: #444; }
[data-theme="dark"] ::-webkit-scrollbar-thumb:hover { background: #666; }

/* Firefox */
* { scrollbar-width: thin; scrollbar-color: #ccc transparent; }
[data-theme="dark"] * { scrollbar-color: #444 transparent; }
```

### 1d. 移动端搜索输入属性

首页和列表页的搜索 `<input>`：

```html
<input type="search"
       enterkeyhint="search"
       autocorrect="off"
       autocapitalize="off"
       spellcheck="false"
       placeholder="搜索 1267 项...">
```

- `type="search"` → iOS 键盘显示"搜索"按钮
- `enterkeyhint="search"` → Android 键盘显示搜索图标
- `autocorrect="off"` → 关闭自动纠错（资源名不会触发）
- `autocapitalize="off"` → 关闭首字母大写
- `spellcheck="false"` → 关闭拼写检查红线

### 1e. 字体渲染优化

```css
body {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
}
```

- `antialiased` / `grayscale` — 消除 Windows/macOS 深色背景下的文字边缘彩边
- `optimizeLegibility` — 启用字距微调和连字，提升长段落可读性

### 1f. 移动端搜索接管的物理返回键 (History API)

当 `.is-searching` 激活时，Android 用户按返回键应退出搜索，而非离开网站：

```js
input.addEventListener('focus', function() {
    if (window.innerWidth <= 768) {
        document.body.classList.add('is-searching');
        window.history.pushState({ search: true }, '');
    }
});

window.addEventListener('popstate', function(e) {
    if (document.body.classList.contains('is-searching')) {
        document.body.classList.remove('is-searching');
        input.blur();
        e.preventDefault();
    }
});
```

- `pushState` 推入虚拟历史记录
- 用户按返回键 → `popstate` 触发 → 移除接管状态 + 收起键盘
- 桌面端不触发接管（`<= 768px` 判断）

### 1g. OpenSearch 浏览器集成

零 UI 成本，允许用户在浏览器地址栏直接搜索 BigPRC 资源。

`<head>` 中添加：
```html
<link rel="search" type="application/opensearchdescription+xml"
      href="/opensearch.xml" title="BigPRC 资源索引">
```

新建 `root/custom-pages/opensearch.xml`：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">
  <ShortName>BigPRC</ShortName>
  <Description>BigPRC 极客资源索引引擎</Description>
  <Url type="text/html" template="https://www.bigprc.com/list.html?q={searchTerms}"/>
  <InputEncoding>UTF-8</InputEncoding>
</OpenSearchDescription>
```

列表页 JS 需读取 URL 参数 `?q=` 自动填入搜索框并触发过滤。用户在地址栏输入 `bigprc.com` → Tab → 输入关键词 → 直接跳转到带搜索结果的列表页。

### 1h. 语义化 HTML

```html
<!-- 首页 -->
<main>       <!-- 替代无意义 div，标记主体内容区 -->
  <h1>BigPRC</h1>     <!-- 每页唯一 h1 -->
</main>

<!-- 详情页 -->
<article>              <!-- 替代 div.details，标记独立资源条目 -->
  <h1>资源名称</h1>
  <time datetime="2026">2026</time>    <!-- 版本/时间信息 -->
  <data value="RAR">RAR</data>         <!-- 结构化数据 -->
</article>

<!-- 列表页 -->
<main>
  <h1>BigPRC 资源湾</h1>
  <table>...</table>
</main>
```

规则：
- 每页只有一个 `<h1>`
- 资源相关内容用 `<article>` 包裹
- 时间/版本用 `<time>` 或 `<data>` 标签
- 主要区域用 `<main>`，非 `<div class="container">`

### 1i. 独立 JSON 文件 + Preload 预加载

**从内联 JSON → 独立文件**。HTML 保持纯净，JSON 可被浏览器独立缓存。

**生成** (`auto_generate.py`):
```python
# 写独立 JSON 文件而非内联 script 标签
import json
with open(os.path.join(web_dir, 'index.json'), 'w', encoding='utf-8') as f:
    json.dump(json_rows, f, ensure_ascii=False)
```

**HTML `<head>` 预加载**:
```html
<link rel="preload" href="/index.json" as="fetch" crossorigin="anonymous">
```

**JS 异步拉取**（首页和列表页共有逻辑）:
```js
var allItems = [];
fetch('/index.json')
    .then(r => r.json())
    .then(data => { allItems = data; initApp(); })
    .catch(() => { /* 降级: 显示静态内容 */ });
```

**收益**:
| 维度 | 内联 JSON | 独立文件 + Preload |
|------|----------|-------------------|
| HTML 大小 | +150KB | 纯净, 只是文本 |
| JSON 缓存 | 随 HTML (短 TTL) | 独立缓存 (长 TTL) |
| 并行加载 | 串行 (HTML 解析阻塞) | 并发 (Preload 提前发起) |
| 架构优雅度 | 混合数据和模板 | 数据和表现分离 |

列表页同样从 `/index.json` 拉取（浏览器第二次访问时直接命中缓存，不产生网络请求）。

**降级策略**: 首页仍渲染静态分类标签和搜索框。JSON 拉取失败时，搜索功能不可用但不影响页面展示。列表页在 JSON 加载前显示 "加载中..."。

### 1j. Nginx 静态资源强缓存

独立 JSON/CSS/JS 文件配置 1 年不可变缓存：

```nginx
# Immutable cache for versioned static assets
# (content hash in filename: index.a8f3c.json)
location ~* \.(json|css|js)$ {
    expires 1y;
    add_header Cache-Control "public, max-age=31536000, immutable";
    access_log off;
}
```

- `immutable` — 告诉浏览器资源永不变，即使硬刷新也不重新验证
- 配合内容 hash 文件名可实现无缝缓存更新
- 当前 HTML 页面缓存策略不变（1 小时）

### 1k. `<noscript>` 优雅降级

在首页搜索区域下方：

```html
<noscript>
    <p style="color: #666; font-size: 13px; text-align: center; margin-top: 16px;">
        检索功能依赖 JavaScript。请启用 JS，或直接浏览
        <a href="/list.html">完整资源列表</a>。
    </p>
</noscript>
```

- JS 禁用时自动显示，正常浏览时不可见
- 提供明确的替代路径（`/list.html` 纯服务端渲染，不依赖 JS）

### 1l. 打印样式 (@media print)

```css
@media print {
    nav, .search-section, button, .cta-button, .download-box,
    .feedback-row, .related-box, .pagination, .footer {
        display: none !important;
    }
    body {
        color: #000;
        background: #fff;
        font-size: 12pt;
        line-height: 1.5;
    }
    a {
        text-decoration: underline;
        color: #000;
    }
    /* 展开链接真实 URL，适合纸质阅读 */
    article a[href^="/"]::after {
        content: " (bigprc.com" attr(href) ")";
        font-size: 0.85em;
        color: #666;
    }
    h1 { font-size: 18pt; page-break-after: avoid; }
    .desc-box { border-left: 1px solid #ccc; background: none; padding-left: 12px; }
    @page { margin: 2cm; }
}
```

- 隐藏导航、按钮、搜索框、相关推荐
- 展开内部链接的真实域名
- 2cm 页边距，符合印刷规范

---

---

## 2. 顶栏导航（替代悬浮按钮 + 回到顶部）

### 结构

```html
<nav>
  <a href="/">BigPRC</a>
  <button>亮色</button>   <!-- 暗色模式显示 "暗色" -->
</nav>
```

### CSS 规范

```css
nav {
    position: sticky; top: 0; z-index: 100;
    display: flex; justify-content: space-between; align-items: center;
    /* 容器无左右 padding —— padding 交给子元素做触控热区 */
    height: 48px;
    background: var(--bg);
    border-bottom: 1px solid var(--border);
}

nav a, nav button {
    /* 隐形触控热区: 菲茨定律最大化 */
    padding: 12px 20px;
    font-size: 14px;
    color: var(--text);
    text-decoration: none;
    background: none;
    border: none;
    cursor: pointer;
    line-height: 24px;  /* 总高度 12+24+12 = 48px = 顶栏高度 */
    /* 移动端触控反馈 */
    -webkit-tap-highlight-color: transparent;
}

nav a:active, nav button:active {
    background: var(--card-bg);  /* #fafafa / #1a1a1a */
    transition: background 0.1s;
}
```

### 规则

- 左边 `BigPRC` 纯文字链接，右边主题切换纯文字按钮
- `justify-content: space-between` 将两者推到屏幕两端 → 左上角和右上角是"无限大"的触控目标
- `:active` 伪类提供瞬时物理反馈，不需要动画
- 无图标、无 logo、无装饰
- 回到顶部按钮删除

---

## 3. CTA 按钮规范（实心 > 空心）

主操作按钮（"获取资源" / "进入网盘"）**默认实心**，不做空心 Ghost Button：

```
默认态:   background: #c0392b; color: #fff; border: none
hover:    opacity: 0.9 (亮) / 0.85 (暗)
:active:  opacity: 0.8

暗色:     background: #e74c3c; color: #121212; border: none
暗hover:  opacity: 0.85
```

- 字体 15px, 字重 600, padding 12px 32px, 圆角 4px
- **无阴影、无渐变、无边框**
- 层级靠色块重量感体现
- 次级操作（如"电脑端普通通道"）仍可用空心边框按钮

---

## 4. 首页

### 桌面端布局

```
           ┌───────────────────────┐
           │                       │
           │      BigPRC           │  ← 36px, 字重 700
           │   极客资源技术索引      │  ← 14px, #666
           │                       │
           │  ┌─────────────────┐  │
           │  │ 搜索 1267 项... │  │  ← 居中, 420px宽, 40px高
           │  └─────────────────┘  │     border 1px #e5e5e5
           │                       │
           │  软件  学习  影视  其他 │  ← 12px, 间距 16px
           │                       │
           │  ┌─ Claudeek ───────┐ │
           │  │ 便携 AI 工作站    │ │  ← 卡片, 1px边框
           │  │ 内测特惠 ¥99 起  │ │
           │  └──────────────────┘ │
           │                       │
           │  索引引擎 · 不存储文件  │  ← 10px, #666
           └───────────────────────┘
```

### 移动端搜索接管 (.is-searching)

当用户在手机上聚焦搜索框时，触发全屏接管：

```
┌─ 顶栏 ─────────────────────────────┐
│ BigPRC                        亮色 │
├────────────────────────────────────┤
│ ┌──────────────────┐  取消          │
│ │ 搜索...          │               │  ← 输入框 + 纯文字"取消"按钮
│ └──────────────────┘               │
├────────────────────────────────────┤
│ 资源标题A               PDF · 12MB  │  ← 左对齐标题(16px) + 右对齐元数据(12px, #666)
│────────────────────────────────────│  ← border-bottom: 1px solid
│ 资源标题B              RAR · 2.3GB  │
│────────────────────────────────────│
│ 资源标题C               ZIP · 8MB   │
│────────────────────────────────────│
│          ...最多 8 条               │
│                                    │
│   未找到匹配项     ← 仅无结果时显示    │
│                                    │
└────────────────────────────────────┘
   剩余空间: 纯色背景遮盖首页其余内容
```

### 接管逻辑

- 父容器添加 `.is-searching` 类
- 搜索区域 `position: sticky; top: 48px`（顶栏下方）
- 结果列表占满剩余视口：`min-height: calc(100dvh - 96px)`
- 列表项 `padding: 14px 20px`（每行 ≥ 48px 触控高度）
- "取消"按钮点击后：清空输入 → 移除 `.is-searching` → 恢复首页布局
- 桌面端不触发接管（保持简单的内联结果下拉）

---

## 5. 详情页

### 布局

```
┌──────────────────────────────────────┐
│                                      │
│  资源名称                             │  ← 22px, 字重 600
│                                      │
│  格式     大小     平台     版本       │  ← 桌面: 4列 grid
│  RAR     2.3GB    Win     2026      │     移动: 2x2 grid
│                                      │
│  ┌────────── 获取资源 ──────────┐     │  ← 实心红底白字按钮
│  └──────────────────────────────┘     │
│                                      │
│  收录于 BigPRC 资源索引引擎             │
│                                      │
│  ───────────────────────────────     │
│  资源描述                             │
│  [SEO 文字段落...]                    │
│                                      │
│  内容由 AI 辅助生成，仅供参考      ← 仅 ai_generated=true     │
│                                      │
│  报告失效  ·  返回资源列表              │
│                                      │
│  ───────────────────────────────     │
│  相关资源                             │
│  · 资源A    · 资源B    · 资源C        │
└──────────────────────────────────────┘
```

### 移动端信息网格

```css
@media (max-width: 768px) {
    .info-grid { grid-template-columns: 1fr 1fr; }  /* 2x2 */
}
```

---

## 6. 中转页

### 布局

```
┌──────────────────────────────────────┐
│                                      │
│  安全验证中                           │  ← 16px
│                                      │
│  [5]                                 │  ← 48px, 字重 700, 主色
│  ────────────────                    │  ← 1px 进度条, width 0→100%
│                                      │     CSS animation 5s linear
│                                      │
│  资源名称                             │
│                                      │
│  ┌────────── 进入网盘 ──────────┐     │  ← 倒计时结束后显示
│  └──────────────────────────────┘     │
│                                      │
│  页面无法跳转？反馈问题                 │
└──────────────────────────────────────┘
```

### 进度条 CSS

```css
.progress-bar {
    width: 0; height: 1px;
    background: var(--primary);    /* #1a365d / #5c9ce6 */
    margin: 16px auto 0;
    max-width: 200px;
    animation: progress 5s linear forwards;
}
@keyframes progress { to { width: 100%; } }
```

- 不用 spinner，不用 emoji
- 纯数字 + 1px 细线进度条提供系统状态反馈
- 去掉所有冗余文案

---

## 7. 列表页

`/list.html` 不挂首页入口，仅通过搜索或直接 URL 访问。

- 保持 JSON 分页 + 标签筛选 + 搜索功能
- 去掉表格中所有 emoji
- 搜索框 placeholder: "搜索..."

---

## 8. 404 页

纯文字，无 emoji：

```
        页面未找到

  该页面可能已被移除或链接有误

      [返回首页]  [浏览资源]
```

---

## 9. 实施清单

| 文件 | 改动 |
|------|------|
| `root/scripts/templates/layout.html` | sticky 顶栏替代悬浮按钮；更新全局 CSS 变量 |
| `root/custom-pages/index.html` | 重写：搜索框 + 移动端 .is-searching 接管 + 分类标签 + 免责 |
| `root/scripts/templates/detail.html` | 实心 CTA 按钮 + 4列→2列移动适配 + 去 emoji |
| `root/scripts/templates/list.html` | 去 emoji，微调样式 |
| `root/scripts/templates/transit.html` | 进度条替代 spinner，精简文案，空心次级按钮 |
| `root/custom-pages/404.html` | 去 emoji，纯文字 |

## 10. 不做的事情

- 不引入任何图标库、SVG 图标、emoji
- 不使用渐变
- 不使用 box-shadow（仅暗色模式下可保留极淡阴影）
- 不引入外部字体
- 不改变现有 URL 路由逻辑

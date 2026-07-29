# BigPRC Visual Language v1.0

> Phase 10.4B-0 — Design System Architecture Freeze
>
> 本文档为 BigPRC 视觉设计系统的唯一事实来源。后续所有组件迁移、页面修改均基于本文档执行，不另行设计。

---

## 1. Design Principles

```
策展 > 收录           Editorial over Aggregation
浏览 > 搜索           Browse over Search
克制 > 丰富           Restraint over Abundance
一致 > 个性           Consistency over Expression
```

| Principle | Do | Don't |
|-----------|-----|-------|
| **克制** | 低饱和色板、1px 边框、无阴影 | 大红大绿、渐变、box-shadow |
| **一致** | 全部使用 Design Token | 硬编码 hex、独立 `:root` |
| **策展** | Card 布局、编辑视角、精选标注 | 数据表格、纯链接列表 |
| **清晰** | 信息层级明确、hover 有反馈 | 静态卡片无交互提示 |

---

## 2. Token System

### 2.1 Primitive Tokens

```
--space-xs  4px       紧密间距
--space-sm  8px       标签/图标间距
--space-md  12px      卡片 gap
--space-lg  16px      标准卡片 padding
--space-xl  20px      卡片标准 padding
--space-2xl 24px      Section 间距
--space-3xl 32px      大区域间距

--radius-sm    4px    输入框、小元素
--radius-md    8px    Card / Panel 主半径
--radius-pill  999px  Badge / Tag / Pill

--border-width  1px   全站统一边框宽度

--transition-fast  0.15s   hover / 交互过渡

--icon-sm  16px  默认图标尺寸
--icon-md  20px  大图标（Hero、空状态）

--opacity-disabled  0.4  禁用态透明度

--font-sans  system-ui, -apple-system, 'Segoe UI', sans-serif
--font-mono  'SF Mono', 'Fira Code', 'Cascadia Code', monospace
```

### 2.2 Semantic Color Tokens

```
Light Theme:
  --color-bg              #ffffff    页面背景
  --color-surface         #fafafa    Card / 容器表面
  --color-text            #1a1a1a    正文
  --color-text-secondary  #666666    辅助文字
  --color-border          #e5e5e5    边框

  --color-accent          #1a365d    主品牌色（深蓝）
  --color-accent-soft     #e8edf3    品牌色浅底

  --color-success         #1a6b4f    成功 / 稳定
  --color-success-soft    #e8f5e9
  --color-warning         #b06000    警告 / 待处理
  --color-warning-soft    #fef9f0
  --color-danger          #c5221f    危险 / 错误
  --color-danger-soft     #fde8e8
  --color-info            #1a56db    信息 / 新发现
  --color-info-soft       #e8f0fe
  --color-neutral         #999999    无数据 / 禁用
  --color-neutral-soft    #f0f0f0

Dark Theme:
  --color-bg              #121212
  --color-surface         #1a1a1a
  --color-text            #e0e0e0
  --color-text-secondary  #999999
  --color-border          #2a2a2a

  --color-accent          #5c9ce6
  --color-accent-soft     #1a2a3a
  --color-success         #4db88d
  --color-success-soft    #1a2f24
  --color-warning         #e0b050
  --color-warning-soft    #2a2218
  --color-danger          #e74c3c
  --color-danger-soft     #2a1a1a
  --color-info            #6b9fff
  --color-info-soft       #1a2240
  --color-neutral         #666666
  --color-neutral-soft    #2a2a2a
```

### 2.3 Legacy Aliases

```
--bg         →  --color-bg
--text       →  --color-text
--secondary  →  --color-text-secondary
--border     →  --color-border
--primary    →  --color-accent
--card-bg    →  --color-surface
--sec        →  --color-text-secondary
--red        →  --color-danger
```

### 2.4 Page-Level Overrides

```
--cta  #c0392b (light) / #e74c3c (dark)
  Defined in: layout.html, index.html
  Purpose: Primary CTA button color (download/purchase actions only)
  NOT part of global tokens — intentionally scoped to CTA buttons
```

---

## 3. Component Rules

### 3.1 Card

**Base**:
```css
.card {
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  transition: border-color var(--transition-fast),
              background-color var(--transition-fast);
}
```

**Variants**:

| Modifier | Default | Hover | Use Case |
|----------|---------|-------|----------|
| *(none)* | — | — | Legacy card, no behavior assumed |
| `.card--interactive` | cursor:pointer | border→accent, bg→`--color-bg` | Clickable cards |
| `.card--static` | cursor:default | no change | Display-only cards |
| `.card--featured` | border:accent | bg→`--color-bg` (if also interactive) | Editor's pick |
| `.card--compact` | padding:`--space-lg` | *(inherits from parent variant)* | Dense layouts |

**Interaction rules**:

```
✅ DO:
  - border-color change on hover (interactive)
  - background-color subtle shift on hover (interactive)
  - cursor:pointer on interactive cards

❌ DON'T:
  - box-shadow (any state)
  - translateY / scale / lift
  - border-width change on hover
  - background color change > 3% lightness delta
```

### 3.2 Button

**Base**:
```css
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  transition: all var(--transition-fast);
  border-radius: var(--radius-md);
  padding: 8px 18px;
}
```

**Variants**:

| Variant | Border | Background | Text Color | Hover |
|---------|--------|------------|-----------|-------|
| `.btn--primary` | none | `--cta` | `#fff` | opacity: 0.9 |
| `.btn--secondary` | `--color-accent` | transparent | `--color-accent` | bg: `--color-accent`, text: `#fff` |
| `.btn--ghost` | none | transparent | `--color-text-secondary` | border: `--color-border` |

**Migration map**:
```
.cta-button     →  .btn.btn--primary
.btn-sub        →  .btn.btn--secondary
.page-btn       →  .btn.btn--ghost
.links a        →  .btn.btn--secondary
.back a         →  text link (not a button)
```

### 3.3 Badge

**Base**:
```css
.badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: var(--radius-pill);
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}
```

**Semantic Variants**:

| Variant | Background | Text Color | Use Case |
|---------|-----------|-----------|----------|
| `.badge--success` | `--color-success-soft` | `--color-success` | Stable, Complete, CORE |
| `.badge--warning` | `--color-warning-soft` | `--color-warning` | Partial, NICHE |
| `.badge--danger` | `--color-danger-soft` | `--color-danger` | Error, THIN, Unstable |
| `.badge--info` | `--color-info-soft` | `--color-info` | Info, SOLID, New |
| `.badge--neutral` | `--color-neutral-soft` | `--color-neutral` | Empty, Unknown |

**Migration**:
- Admin `qColor()` → badge variant (CORE=success, SOLID=info, NICHE=warning, THIN=danger, EMPTY=neutral)
- Admin `hColor()` → badge variant (stable=success, warning=warning, unstable=danger, empty=neutral, broken=danger)
- Admin `actionStyle()` → badge variant (KEEP=success, EXPAND_RULE=warning, NEW_COLLECTION=info, MERGE_REVIEW=danger)
- Collection hero `.badge` → `.badge.badge--neutral`

### 3.4 Tag

**Base** (single definition — replaces `.tag`, `.ed-meta-tag`, `.tag-item`):
```css
.tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 12px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  border: var(--border-width) solid var(--border);
  color: var(--color-text-secondary);
  background: var(--color-bg);
}
```

**No variants** — Tag is a single-purpose component: content classification label.
Color is always mute/secondary. If you need semantic color, use Badge.

### 3.5 Pill

**Base** (interactive filter chip):
```css
.pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: var(--radius-pill);
  font-size: 12px;
  cursor: pointer;
  border: var(--border-width) solid var(--border);
  color: var(--color-text-secondary);
  background: var(--color-bg);
  font-family: inherit;
  transition: all var(--transition-fast);
}
.pill.active {
  background: var(--color-accent);
  color: #fff;
  border-color: var(--color-accent);
}
```

**Migration**:
- `.filter-pill` → `.pill`
- `.filters button` → `.pill`

---

## 4. Icon Rules

### 4.1 System

- **Library**: Lucide (https://lucide.dev)
- **CDN**: `<script src="https://unpkg.com/lucide@latest"></script>`
- **Usage**: `<i data-lucide="icon-name"></i>`
- **Init**: `lucide.createIcons()` after DOM ready

### 4.2 Sizing

| Size | Value | Usage |
|------|-------|-------|
| Default | `16px` (`var(--icon-sm)`) | Inline with text, badges, buttons |
| Medium | `20px` (`var(--icon-md)`) | Section headers, Hero, empty states |

### 4.3 Color

```css
.icon-success  { color: var(--color-success); }
.icon-warning  { color: var(--color-warning); }
.icon-danger   { color: var(--color-danger); }
.icon-info     { color: var(--color-info); }
.icon-neutral  { color: var(--color-neutral); }
.icon-accent   { color: var(--color-accent); }
.icon-muted    { color: var(--color-text-secondary); }
```

### 4.4 Icon + Text Layout

```html
<span class="icon-label">
  <i data-lucide="pencil-line" class="icon-muted"></i>
  编辑视角
</span>
```

```css
.icon-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
```

### 4.5 When NOT to use icons

- ❌ Pure data values in tables (e.g., file size, date)
- ❌ Category/tag text labels (use `.tag` component)
- ❌ Inline paragraph text
- ❌ Link text in navigation

### 4.6 Full Emoji → Lucide Map

See `root/custom-pages/js/icon-system.js` for the complete mapping.

---

## 5. Interaction Rules

### 5.1 Hover

```
Interactive elements (cards, buttons, pills):
  ✅ border-color change
  ✅ background-color subtle shift
  ✅ cursor:pointer

Static elements (display cards, badges, tags):
  ❌ no hover change
  ❌ cursor:default
```

### 5.2 Focus

```
✅ :focus-visible outline (browser default or custom 2px outline)
❌ No custom focus ring that removes browser outline
```

### 5.3 Disabled

```
✅ opacity: var(--opacity-disabled)
✅ cursor: not-allowed
✅ pointer-events: none
```

### 5.4 Motion

```
✅ transition: var(--transition-fast) on color/background/border
❌ No transform animations (translate, scale, rotate)
❌ No box-shadow transitions
```

---

## 6. Typography

### 6.1 Font Stack

| Token | Value | Usage |
|-------|-------|-------|
| `--font-sans` | `system-ui, -apple-system, 'Segoe UI', sans-serif` | 全站正文、标题、UI |
| `--font-mono` | `'SF Mono', 'Fira Code', 'Cascadia Code', monospace` | CLI 提示、代码 |

### 6.2 Type Scale (reference)

```
Hero title:   32px / 800 / -0.3px
Page title:   22-24px / 600-700
Section h2:   15-18px / 600-700
Section h3:   14px / 600
Body:         13-14px / 400
Small/caption: 11-12px / 400-500
```

---

## 7. Do / Don't Examples

### Card

```
✅ DO:
<div class="card card--interactive" onclick="...">
  <h3>Card Title</h3>
  <p>Description text</p>
</div>

❌ DON'T:
<div class="card" style="box-shadow: 0 2px 8px rgba(0,0,0,0.1)">
<div class="card" onmouseover="this.style.transform='translateY(-4px)'">
```

### Badge

```
✅ DO:
<span class="badge badge--success">CORE</span>
<span class="badge badge--warning">待审核</span>

❌ DON'T:
<span class="badge" style="background:#e8f5e9;color:#1a6b4f">CORE</span>
<span style="padding:2px 10px;border-radius:10px">manual badge</span>
```

### Button

```
✅ DO:
<a href="..." class="btn btn--primary">获取资源</a>
<button class="btn btn--secondary">取消</button>

❌ DON'T:
<a href="..." class="cta-button"> (use .btn.btn--primary)
<button style="padding: 8px 14px; border: 1px solid...">
```

### Icon

```
✅ DO:
<span class="icon-label">
  <i data-lucide="pencil-line" class="icon-muted"></i>
  编辑视角
</span>

❌ DON'T:
<span>📝 编辑视角</span>
<span>✍️ 编辑</span> (inconsistent with 📝)
```

### Color

```
✅ DO:
color: var(--color-danger);
background: var(--color-success-soft);

❌ DON'T:
color: #c0392b;
background: #e8f5e9;
```

---

## 8. File Architecture

```
_tokens.css                             ← CANONICAL SOURCE
  ├── sync_tokens.sh / .ps1
  └── design-tokens.css                 ← synced copy for standalone pages

icon-system.js                          ← emoji→Lucide map (reference doc)

Consumers:
  layout.html  → {% include "_tokens.css" %}
  index.html   → <link href="/css/design-tokens.css">
  admin/*.html → <link href="/css/design-tokens.css">
```

---

## 9. Phase 10.4B Implementation Order

| # | Phase | Scope | Files | Priority |
|---|-------|-------|-------|----------|
| **1** | **Color Map → Token** | JS 硬编码 hex → CSS Variable | 6 Admin pages | 🔴 P0 |
| **2** | **Card Interaction** | `.card` hover bg shift in layout.html | `layout.html` | 🔴 P0 |
| **3** | **Badge Component** | 3 badge sets → 1 + 5 variants | `_tokens.css` + 4 Admin + collection.html | 🟡 P1 |
| **4** | **Button Component** | 5 button styles → 3 types | `_tokens.css` + detail + transit + list + 3 Admin | 🟡 P1 |
| **5** | **Icon Migration** | Emoji → Lucide | 5 templates + 6 Admin + favicon | 🟡 P1 |
| **6** | **Tag Unification** | .tag/.ed-meta-tag/.tag-item → .tag | `_tokens.css` + collection + collection-detail | 🟢 P2 |
| **7** | **Favicon** | New brand SVG favicon | `favicon.svg` + layout.html | 🟢 P2 |

**Principle**: Each phase is self-contained — no phase depends on a later one. Can be executed independently and verified before proceeding.

---

> **Document version**: v1.0
> **Status**: FROZEN — Architecture lock. No new components without updating this document first.
> **Next**: Phase 10.4B-1 Color Map → Token

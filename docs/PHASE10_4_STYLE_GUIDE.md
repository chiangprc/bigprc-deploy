# BigPRC UI Style Guide — Phase 10.4

> **Direction**: Calm, editorial, minimal.  
> **References**: Notion, Linear, Vercel, Apple HIG.  
> **Principle**: Borders almost invisible. Elevation comes from spacing, not decoration.

---

## 1. Typography

```
H1 — 28px / 800 — Page hero
  BigPRC 策展
  ─────────────────

H2 — 18px / 700 — Section header
  编辑视角
  ─────────

H3 — 15px / 600 — Card title
  BBC 自然纪录片

Body — 14px / 400 — Paragraph text
  BBC自然纪录片系列将镜头对准地球的脉搏，从深海到高原，从雨林到极地...

Meta — 12px / 400 — Secondary info, counts
  315 个资源 · 自然科学

Caption — 11px / 400 — Badges, tags, footnotes
  已发布 · 编辑精选
```

**Font stack**: `system-ui, -apple-system, 'Segoe UI', sans-serif`
**Line height**: 1.6 (body), 1.4 (headings)
**Letter spacing**: -0.3px (H1 only)

---

## 2. Color Tokens

```
Light mode:
  --bg:           #ffffff    Page background
  --text:         #1a1a1a    Primary text
  --secondary:    #666666    Secondary text, meta
  --border:       #e5e5e5    Card borders, dividers
  --surface:      #fafafa    Card background
  --accent:       #1a6b4f    Primary accent (links, featured)
  --accent-soft:  #e8f5e9    Badge background (success)
  --amber:        #b06000    Warning text
  --amber-soft:   #fef9f0    Warning background
  --red:          #c5221f    Danger text
  --red-soft:     #fde8e8    Danger background

Dark mode:
  --bg:           #121212
  --text:         #e0e0e0
  --secondary:    #999999
  --border:       #2a2a2a
  --surface:      #1a1a1a
  --accent:       #4db88d
  (amber/red remain sufficiently visible in dark mode)
```

---

## 3. Spacing Scale

```
4px   — inline gap (badge → text, icon → label)
8px   — compact gap (card grid gap, filter pills)
12px  — default padding (card internal, section internal)
16px  — relaxed (section margins)
24px  — wide (between major sections)
32px  — hero spacing (above/below H1)
48px  — page top/bottom padding
```

---

## 4. Radius Scale

```
4px   — buttons, inputs
6px   — compact cards (admin lists)
8px   — standard cards (collection, spotlight, editorial)
12px  — badges, tags, pills
∞     — hero section (no radius — full width)
```

**Rule**: Every card on the site uses 8px border-radius. No exceptions. No 10px, no 14px.

---

## 5. Shadow Scale

```
None         — default (no shadow)
.card:hover  — box-shadow: 0 1px 3px rgba(0,0,0,0.06)
```

**Rule**: Only one shadow. Only on hover. Used only on clickable cards. No decorative shadows anywhere else.

---

## 6. Border Rules

```
Card default:    1px solid var(--border)
Card hover:      1px solid var(--accent)
Featured card:   1px solid var(--accent)  ← subtle full-border, NOT 3px left bar
Input focus:     1px solid var(--accent) + 0 0 0 3px var(--accent-soft)
Divider:         1px solid var(--border)  (bottom border only, never top or full)
```

**Rule**: No thick left accent borders anywhere on the site. Featured cards use a subtle full-border accent color. Distinction comes from spacing and typography, not decoration.

---

## 7. Card Specification

### Single Card Component

```
┌──────────────────────────────────────┐
│                                      │  ← 8px border-radius
│  H3: BBC 自然纪录片                   │  ← 15px / 600
│  Meta: 315 个资源 · 自然科学          │  ← 12px / 400 / --secondary
│                                      │  ← 20px 24px padding
└──────────────────────────────────────┘  ← 1px --border
                                         ← --surface background
  hover → border becomes --accent         ← 0 1px 3px shadow
  featured → border always --accent
```

### CSS

```css
.card {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px 24px;
    background: var(--surface);
    transition: border-color 0.15s, box-shadow 0.15s;
}
.card:hover {
    border-color: var(--accent);
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.card--featured {
    border-color: var(--accent);
}
.card--compact {
    padding: 14px 18px;
}
```

### Where .card replaces existing classes

| Old Class | New |
|-----------|-----|
| `.coll-card` | `.card` |
| `.ed-card` | `.card` |
| `.hl-card` | `.card` |
| `.spotlight-card` (inline) | `.card` |
| `.product-card` | `.card .card--compact` |
| `.card` (admin dashboard) | `.card .card--compact` |

### Visual comparison

```
BEFORE (thick left accent):              AFTER (subtle full-border):
┃ BBC 自然纪录片                           ┌ BBC 自然纪录片 ──────────┐
┃ 315 个资源                              │ 315 个资源               │
┃                                        └──────────────────────────┘
┃ (3px solid --primary)                  (1px solid --accent)
```

---

## 8. Button Specification

```
Primary:   [ 探索专题 ]     bg=accent, white text, 6px radius, 10px 20px padding
Ghost:     [ 返回列表  ]     border, --text color, 6px radius, 8px 16px padding
Text:      返回首页 →        no border, --accent color, no padding
```

### CSS

```css
.btn {
    display: inline-block;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: opacity 0.15s;
    text-decoration: none;
}
.btn--primary { background: var(--accent); color: #fff; padding: 10px 20px; border: none; }
.btn--ghost   { border: 1px solid var(--border); color: var(--text); padding: 8px 16px; background: transparent; }
.btn--text    { color: var(--accent); padding: 0; border: none; background: none; }
```

---

## 9. Badge Specification

```
Published:  [ 已发布 ]  bg=accent-soft, color=accent, 12px radius, 3px 12px padding
Draft:      [  草稿  ]  bg=amber-soft,  color=amber
Rejected:   [  退回  ]  bg=red-soft,    color=red
Category:   [ 自然科学 ] border only,    color=secondary, 12px radius, 2px 10px padding
```

### CSS

```css
.badge {
    display: inline-block;
    border-radius: 12px;
    padding: 3px 12px;
    font-size: 11px;
    font-weight: 500;
}
.badge--success  { background: var(--accent-soft); color: var(--accent); }
.badge--warning  { background: var(--amber-soft);  color: var(--amber);  }
.badge--danger   { background: var(--red-soft);    color: var(--red);    }
.badge--neutral  { border: 1px solid var(--border); color: var(--secondary); background: transparent; }
```

---

## 10. Icon Specification

### Library: Lucide Icons

**CDN**: `<script src="https://unpkg.com/lucide@latest"></script>`
**Usage**: `<i data-lucide="star" style="width:16px;height:16px"></i>`
**Color**: `currentColor` (inherits from parent text color)
**Size**: 16px (inline), 20px (standalone), 24px (hero)

### Icon Map

```
Page section          Current emoji    Lucide icon
─────────────────────────────────────────────────
编辑视角               📝               pen-line
编辑精选               🌟               star
收藏理由               ⭐               bookmark
适合人群               👥               users
常见问题               💬               message-circle
相关专题               🔗               link
自然探索               🌍               globe
人文经典               📚               library
效率工具               🛠               wrench
学习成长               🎓               graduation-cap
其他探索               🔍               search
状态已发布              ✅               check-circle
状态草稿               🟡               circle (amber)
状态已审核              🔵               circle (accent)
状态退回               🔴               circle (red)
```

### Rule

**No color in icons.** Every icon inherits `currentColor`. Status distinction comes from badge color, not icon color.

---

## 11. Interaction States

```
Link (default):    color: var(--accent), text-decoration: none
Link (hover):      text-decoration: underline

Card (default):    border: 1px solid var(--border)
Card (hover):      border-color: var(--accent), subtle shadow

Button primary (hover):  opacity: 0.9
Button ghost (hover):    border-color: var(--accent), background: var(--surface)

Input (default):   border: 1px solid var(--border), border-radius: 6px
Input (focus):     border-color: var(--accent), box-shadow: 0 0 0 3px var(--accent-soft)

Details summary (hover): color: var(--accent)
```

---

## 12. Frontend + Admin Consistency

### Admin pages use the same design tokens

```
Admin dashboard cards:     .card .card--compact
Admin status badges:       .badge--success / .badge--warning / .badge--danger
Admin table rows:          background: transparent, hover → var(--surface)
Admin navigation:          .btn--ghost
Admin section headers:     H2 (18px / 700), same as frontend
```

**Rule**: If a component exists on the frontend, the admin uses the same component. No admin-only variations.

---

## 13. Implementation Phases (Coding Order)

| Phase | Scope | Files | Lines |
|-------|-------|-------|-------|
| **10.4A** | Define `.card` + modifiers in `layout.html`. Replace all card classes on frontend pages. Remove left accent borders. | `layout.html`, `collection.html`, `collection_index.html`, `detail.html`, `list.html` | ~50 |
| **10.4B** | Replace admin inline card styles with `.card`. Unify badge styles across admin pages. | `dashboard.html`, `collections.html`, `editorial.html`, `collection-review.html`, `collection-detail.html`, `editorial-detail.html` | ~40 |
| **10.4C** | Add Lucide CDN. Replace emoji with Lucide icons on frontend + admin. | All templates | ~30 |
| **10.4D** | Color consolidation. Remove unused CSS variables. | `layout.html`, admin pages | ~15 |

**Total**: ~135 lines. Zero schema/pipeline/JS changes.

---

确认后从 Phase 10.4A 开始。
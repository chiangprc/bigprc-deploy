# Phase 10.5 — Visual Consistency Audit Report

> Step 1: Analysis only. No code changes.

---

## 1. Emoji / Icon Migration Status

### 1.1 HTML Emoji (Scope)

| File | Emoji | Context | Count |
|------|-------|---------|-------|
| `admin/editorial-detail.html` | 📄 | "未找到专题" error state | 1 |
| `tools/claudeek.html` | 📝 🎓 | Capability cards | 2 (out of scope) |

**Total in-scope HTML: 1 emoji** (was missed in Phase 10.4B-5)

### 1.2 Python Emoji — CRITICAL

**26 Python files** contain emoji. These are data generators — the emoji flow into JSON data files and rendered HTML. Key offenders:

| File | Emoji | Count |
|------|-------|-------|
| `auto_generate.py` | 🎓 🛠 🌍 | 3 (collection theme icons) |
| `collection_dashboard_export.py` | ✅ 🔧 📋 📚 ✍️ 🌐 🟢 🟡 🔴 | ~15 |
| `collection_review_export.py` | ✅ 🔧 🆕 🔀 💡 | ~10 |
| `collection_editor_ai.py` | 📝 | ~3 |
| `ai_seo_writer.py` | ✅ | ~20 |
| `collection_faq.py` | ✅ | ~10 |
| Others (20 files) | Various | ~30 |

**Total Python emoji: ~90 instances across 26 files.**

### 1.3 Root Cause

Python scripts generate:
- `admin/data/dashboard.json` — contains emoji strings
- `admin/data/review-data.json` — contains emoji strings
- `admin/data/editorial.json` — contains emoji strings
- Collection page HTML — emoji in theme names

These emoji then flow into admin pages via JS-rendered HTML.

### 1.4 Migration Plan

| Layer | Action |
|-------|--------|
| Python data generators | Replace emoji string literals with Lucide icon name strings (`'✅' → 'circle-check'`) |
| Python theme config | Replace emoji with semantic names (`'🎓' → 'graduation-cap'`) |
| HTML rendering | Use `BPRC.icon()` in JS; use `<i data-lucide>` in templates |
| JSON data files | Regenerate — emoji will be gone after Python fix |

---

## 2. Typography Audit

### 2.1 Hardcoded font-size by File

| File | Count | Worst offenders |
|------|-------|----------------|
| `collection-detail.html` | 29 | JS inline font-sizes (11/12/13/14/15/20/22/24/48px) |
| `collection.html` | 23 | CSS rules (11/12/14/15/16/18/26/32px) |
| `index.html` | 17 | CSS + inline (11/12/14/15/16/26/28/36px) |
| `detail.html` | 13 | CSS rules (11/12/13/14/15/22px) |
| `collection-review.html` | 10 | CSS + inline (11/12/13/14/15/22/28px) |
| `list.html` | 9 | CSS (12/13/14/16/22px) |
| `editorial.html` | 7 | CSS (11/12/13/20px) |
| `collection_index.html` | 6 | CSS (12/14/16/18/24px) |
| `editorial-detail.html` | 5 | CSS (13/14/22px) |
| `dashboard.html` | 3 | CSS (12/20/32px) |
| `collections.html` | 3 | CSS (11/13/20px) |
| `transit.html` | 3 | CSS (13/15/48px) |
| `layout.html` | 2 | print media query (12pt) |

**Total: ~130 hardcoded font-size instances across 13 files.**

### 2.2 Type Scale Gap Analysis

```
Token           Target    Current Non-Token Sizes in Use
─────────────────────────────────────────────────────────
--text-caption   11px  ✅  11px matches
--text-meta      12px  ✅  12px matches
--text-body      14px  ⚠️  13px (2 instances — table fallback), 15px (1 — input)
--text-subtitle  16px  ⚠️  15px (not in scale)
--text-section   18px  ✅  18px matches
--text-title     22px  ⚠️  20px, 24px (not in scale), 20px→18px already migrated
--text-hero      32px  ⚠️  26px, 28px, 36px (not in scale)
--text-display   48px  ✅  48px matches
```

**Non-scale sizes to eliminate**: 10px, 13px, 15px, 20px, 24px, 26px, 28px, 36px

### 2.3 Migration Plan

| Current | → | Token | Scope |
|---------|---|-------|-------|
| `10px` | → | `11px` (--text-caption) | 1 |
| `13px` | → | `12px` (--text-meta) or `14px` (--text-body) by context | 2 |
| `15px` | → | `16px` (--text-subtitle) | 1 remaining |
| `20px` | → | `18px` (--text-section) | admin h1 |
| `24px` | → | `22px` (--text-title) | collection_index h1 |
| `26px` | → | `22px` (--text-title) | 1 stat number |
| `28px` | → | `22px` (--text-title) mobile | mobile h1 |
| `36px` | → | `32px` (--text-hero) | 1 hero h1 |
| `48px` | → | keep (--text-display) | countdown |

---

## 3. Collection Card Analysis

### 3.1 Current State (`collection_index.html`)

```css
.coll-grid { grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
/* .card from _tokens.css provides: border, border-radius:8px, background:--color-surface */
/* .card from layout.html provides: padding:20px 24px */

.coll-card h3       { font-size: 16px; }   /* title — ✅ correct */
.coll-card .intro   { font-size: 12px; }   /* desc — 🔴 too small, should be 14px */
.coll-card .count   { font-size: 12px; }   /* meta — ✅ correct */
```

### 3.2 Problems

| # | Issue | Detail |
|---|-------|--------|
| C1 | Description font too small | 12px for 80-char intro text is hard to read |
| C2 | No min-height | Cards with short intro vs long intro have different heights |
| C3 | No icon | BPRC.icon migration missed theme section icons (🎓🛠🌍) that are in Python |
| C4 | Dense gap | 12px gap between cards feels cramped |
| C5 | No visual weight for count | Count is same size as intro text |

### 3.3 Target State

```
.card {
  border: var(--border-width) solid var(--color-border);
  border-radius: var(--radius-md);       /* 8px */
  background: var(--color-surface);
  padding: var(--space-2xl);              /* 24px — unified */
  transition: border-color var(--transition-fast),
              background-color var(--transition-fast);
  min-height: 140px;                      /* consistent card height */
  display: flex;
  flex-direction: column;
}

.coll-card h3     { font-size: var(--text-subtitle); }   /* 16px, 2-line max */
.coll-card .intro { font-size: var(--text-body);         /* 14px, line-height:1.6 */
                    line-height: 1.6; }
.coll-card .count { font-size: var(--text-meta); }       /* 12px, pushed to bottom */
.coll-grid         { gap: var(--space-lg); }             /* 16px gap — breathing room */
```

---

## 4. Visual Audit Script Design

### 4.1 `scripts/visual_audit.py`

```python
#!/usr/bin/env python3
"""BigPRC Visual Audit — checks emoji, font-size, color, card compliance."""
import os, re, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def check_emoji():
    """Scan for emoji characters in HTML and Python files."""
    ...

def check_font_size():
    """Find hardcoded font-size: XXpx not using var(--text-*)."""
    ...

def check_color():
    """Find hardcoded hex colors in business code."""
    ...

def check_card():
    """Verify .card usage and modifier correctness."""
    ...

def main():
    results = {
        'emoji': check_emoji(),
        'font_size': check_font_size(),
        'color': check_color(),
        'card': check_card()
    }
    # Output PHASE10_5_VISUAL_AUDIT.md
```

---

## 5. Execution Plan

### Phase 10.5-1: Icon Migration Complete

| Scope | Files | Emoji Count |
|-------|-------|-------------|
| HTML (scope) | `editorial-detail.html` | 1 |
| Python generators | 26 `.py` files | ~90 |
| JSON data | regenerate | 0 after Python fix |

Mapping table:
```
🎓 → graduation-cap        (学习成长)
🛠 → wrench                 (效率工具)
🌍 → globe                  (自然探索)
✅ → circle-check           (成功/完成/已覆盖)
🔧 → wrench                 (优化/完善)
📋 → list                   (列表/Discovery)
📚 → library                (专题管理)
✍️ → pencil-line            (编辑)
🌐 → globe                  (前台)
🟢 → circle-check           (稳定)
🟡 → alert-circle           (警告/部分)
🔴 → circle-x               (危险/错误)
⚪ → circle                  (无数据)
💡 → terminal               (CLI提示)
```

### Phase 10.5-2: Typography Completion

130 hardcoded font-size → Type Scale tokens.

Priority: Title/Subtitle/Section levels first, then Meta/Caption.

### Phase 10.5-3: Collection Card Refinement

3 files: `collection_index.html`, `_tokens.css`, Python theme config.

---

> **Status: AUDIT COMPLETE — awaiting confirmation to proceed with Phase 10.5-1.**

# Phase 10.4D Architecture Plan — Typography & Responsive

> Status: FROZEN — Architecture lock.
> Do NOT implement until confirmed.

---

## 1. Current Problems (from Phase 10.4C Audit)

| # | Severity | Problem |
|---|----------|---------|
| T1 | P1 | No unified Type Scale — 11/12/13/14/15/16px all in use, adjacent sizes stacked |
| T2 | P1 | `font-size:13px` is the most-used size (50 instances) but undefined as a token |
| M1 | P0 | All 6 Admin pages lack any responsive design — unusable on mobile |
| M2 | P0 | Admin tables (5-7 columns) have no horizontal scroll strategy |
| B1 | P1 | Hero badge uses `var(--accent)` colors but Badge system has no `.badge--accent` |
| N1 | P1 | Navigation links (`.coll-link`, `.back a`) not connected to unified interaction system |

---

## 2. Design Principles

```
1. Token First — Every type/space/color decision originates from a token
2. Progressive Enhancement — Desktop-first admin, mobile as constraint layer
3. Shared Foundation — Admin pages share ONE responsive strategy, not 6 independent fixes
4. Semantic Naming — Tokens named by usage (--text-sm), not by value (--text-12px)
5. Minimal Migration — Type Scale replaces inline font-size values surgically
```

---

## 3. Typography — Type Scale Design

### 3.1 Current Distribution

```
11px (18 instances): badges, captions, small meta, error messages
12px (46 instances): tags, table data, secondary text, filter pills, pagination, meta labels
13px (50 instances): body text, table headers, admin labels, nav links, subtitles
14px (32 instances): section text, btn--primary, collection description, button labels, form inputs
15px (7 instances):  btn--primary (detail/transit), editorial note, section h2, card title
16px (7 instances):  section h2, countdown, page subtitle
18px (5 instances):  section h2, faq h2, theme-section h2
20px (7 instances):  page h1 (admin), dashboard stat values
22px (5 instances):  page h1 (detail, list, collection-detail, review)
24px (3 instances):  page h1 (collection-index), mobile h1 (collection)
26px (1 instance):   stat number (collection hero)
28px (3 instances):  mobile h1 (index), dashboard stat number
32px (2 instances):  hero h1 (collection)
36px (1 instance):   hero h1 (index)
48px (3 instances):  countdown (transit), empty state icon
```

### 3.2 Usage Classification

| Category | Current Range | Typical Context |
|----------|--------------|-----------------|
| **Caption** | 10-11px | badge text, error footnotes, fine print |
| **Meta** | 12px | tags, table data, filter pills, pagination |
| **Body** | 13-14px | paragraph text, admin labels, nav links |
| **Subtitle** | 15-16px | section desc, card subtitles, lead text |
| **Section Title** | 16-18px | h2, faq title, theme section |
| **Page Title** | 20-24px | h1, dashboard stat values |
| **Hero** | 28-36px | hero h1 |
| **Display** | 48px | countdown, empty state |

### 3.3 Recommended Type Scale

```css
:root {
    --text-caption:  11px;   /* badge, error footnote, fine print */
    --text-meta:     12px;   /* tag, table cell, filter pill, pagination */
    --text-body:     14px;   /* paragraph, label, nav link (13px→14px) */
    --text-subtitle: 16px;   /* section desc, lead text, card subtitle */
    --text-section:  18px;   /* h2, faq title */
    --text-title:    22px;   /* page h1 */
    --text-hero:     32px;   /* hero h1 */
    --text-display:  48px;   /* countdown, empty state icon */
}
```

**Key migration rule**: `13px → 14px` (`--text-body`). This is the biggest single change: 50 instances of 13px become 14px. This is a readability improvement — 13px is a non-standard size on the system-ui font stack.

### 3.4 Weight Scale (keep as-is, already consistent)

```
--weight-normal:  400   /* body text (rarely used) */
--weight-medium:   500   /* badges, tags, secondary text */
--weight-semibold: 600   /* section titles, card titles, buttons */
--weight-bold:     700   /* page titles, hero, stat numbers */
--weight-extrabold:800   /* hero h1 (collection) */
```

### 3.5 Migration Rules

| Current | → | Target Token | Scope |
|---------|---|-------------|-------|
| `font-size:10px` | → | `var(--text-caption)` (no-op) | 1 instance |
| `font-size:11px` | → | `var(--text-caption)` | 18 instances (badge already uses this via component) |
| `font-size:12px` | → | `var(--text-meta)` | 46 instances (tag + table already use this via component) |
| `font-size:13px` | → | `var(--text-body)` (=14px) | **50 instances** — largest batch |
| `font-size:14px` | → | `var(--text-body)` | 32 instances (no-op) |
| `font-size:15px` | → | `var(--text-subtitle)` (=16px) | 7 instances — minor bump |
| `font-size:16px` | → | `var(--text-subtitle)` | 7 instances (no-op) |
| `font-size:18px` | → | `var(--text-section)` | 5 instances (no-op) |
| `font-size:20px` | → | `var(--text-section)` (=18px) | 7 instances — minor reduction |
| `font-size:22px` | → | `var(--text-title)` | 5 instances (no-op) |
| `font-size:24px` | → | `var(--text-title)` | 3 instances (no-op) |
| `font-size:26px` | → | `keep as exception` | 1 instance (stat number — unique context) |
| `font-size:28px` | → | `var(--text-title)` | 3 instances (mobile h1) |
| `font-size:32px` | → | `var(--text-hero)` | 2 instances |
| `font-size:36px` | → | `var(--text-hero)` | 1 instance |
| `font-size:48px` | → | `var(--text-display)` | 3 instances |

**Impact assessment**: The `13px→14px` migration affects body text readability positively. The `15px→16px` bump is minor. The `20px→18px` reduction for admin page titles is subtle — admin h1 goes from 20px to 18px, which is still clearly larger than body.

---

## 4. Admin Responsive Architecture

### 4.1 Audit Summary

| Page | @media queries | Table overflow | Grid collapse | Touch targets |
|------|---------------|----------------|---------------|---------------|
| dashboard | 1 (cards only) | N/A | ✅ 4→2 cols | ❌ |
| collections | 0 | ❌ 6 cols, no scroll | N/A | ❌ |
| collection-review | 1 (summary only) | ❌ sample tables | ✅ 4→2 cols | ❌ |
| collection-detail | 1 (cards only) | ❌ shared+sample tables | ✅ 4→2 cols | ❌ |
| editorial | 1 (cards only) | ❌ 8 cols, no scroll | ✅ 4→2 cols | ❌ |
| editorial-detail | 0 | N/A | N/A | ❌ |

### 4.2 Strategy: Shared Responsive Foundation

**DO NOT** create 6 separate responsive patches.

**DO** add ONE shared admin-responsive foundation to `design-tokens.css`.

```
Breakpoint: 768px (tablet/mobile threshold)
Strategy:   Desktop-first. Mobile overrides via max-width media query.
```

### 4.3 Breakpoint Strategy

```css
/* Admin responsive foundation — added to _tokens.css */
@media (max-width: 768px) {
    /* Layout */
    .wrap { padding: 16px 12px; }

    /* Tables */
    .table-wrap {
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }
    table { min-width: 600px; } /* force horizontal scroll for wide tables */

    /* Cards grid */
    .cards {
        grid-template-columns: repeat(2, 1fr);
    }

    /* Actions row */
    .links, .toolbar {
        flex-direction: column;
        align-items: stretch;
    }
    .links .btn, .toolbar .btn {
        width: 100%;
        justify-content: center;
    }

    /* Hide non-critical columns */
    .hide-mobile { display: none; }

    /* Touch-friendly */
    .btn, .badge, .tag, .pill {
        min-height: 44px;
        align-items: center;
    }
    td a, th {
        padding: 10px 6px;
        min-height: 44px;
    }
}
```

### 4.4 Table Horizontal Scroll

Each admin table page wraps `<table>` in `<div class="table-wrap">`. The global responsive CSS provides `overflow-x:auto`.

Admin pages with tables:
- `collections.html` — main resource table → wrap in `.table-wrap`
- `editorial.html` — editorial status table → wrap in `.table-wrap`
- `collection-detail.html` — shared collections + sample tables → wrap in `.table-wrap`
- `collection-review.html` — sample tables → already have wrapper class

**Impact**: JS-generated table HTML needs one wrapping `<div class="table-wrap">` added. Minimal code change.

### 4.5 Card Grid Collapse

All admin stat cards use `.cards` class with `grid-template-columns: repeat(4, 1fr)`. The responsive rule collapses to 2 columns at 768px. Already partially implemented in 2 pages — extended to all 6.

### 4.6 Mobile Padding

- Desktop: `padding: 24px 20px` (collections/collection-detail/editorial-detail) or `padding: 32px 20px` (dashboard/collection-review/editorial)
- Mobile: **unified** `padding: 16px 12px`

---

## 5. Badge Accent Variant

### 5.1 Problem

`collection.html` Hero badge:
```css
.hero .badge { background: var(--accent-soft); color: var(--accent); }
```

This uses accent colors but the Badge system has no accent variant. The Hero badge is a legitimate semantic use case — "BigPRC 策展" is a brand label, not a status indicator.

### 5.2 Solution

Add `.badge--accent` to `_tokens.css`:

```css
.badge--accent { background: var(--color-accent-soft); color: var(--color-accent); }
```

Then simplify collection.html:
```css
/* Before: .hero .badge { background: var(--accent-soft); color: var(--accent); padding: 4px 14px; ... } */
/* After:  .hero .badge { padding: 4px 14px; font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 16px; } */
```

HTML: `<div class="badge badge--accent">BigPRC 策展</div>`

### 5.3 Full Badge Variant Set (after addition)

```
badge--success   green
badge--warning   amber
badge--danger    red
badge--info      blue
badge--neutral   gray
badge--accent    deep blue (brand)  ← NEW
```

---

## 6. Navigation Action System

### 6.1 Audit

| Pattern | Current | Should Be | Reason |
|---------|---------|-----------|--------|
| `.coll-link` ("浏览全部") | Plain `<a>` with `color:var(--primary)` | `.btn.btn--ghost` | It's a CTA to browse all — same semantic as pagination |
| `.back a` ("← 返回") | Plain `<a>` with `color:var(--primary)` | Keep as text link | Breadcrumb navigation — not an action, just navigation |
| Admin page footer nav links | `.btn.btn--secondary` ✅ | Already correct | — |
| `detail.html` "返回资源列表" | `.back-link` plain `<a>` | Keep as text link | Inline navigation, low priority |

### 6.2 Principle

```
Button = Action (submit, navigate to a tool, trigger behavior)
Link   = Navigation (go back, browse content, breadcrumb)
```

- `.coll-link` → Button (it's a browse-all CTA, equivalent to pagination)
- `.back a` → Link (it's breadcrumb navigation, keep as-is)
- `.back-link` → Link (same)

---

## 7. File Impact Summary

| Phase | Files Modified | Files Created |
|-------|---------------|---------------|
| 10.4D-1: Type Scale | `_tokens.css`, `design-tokens.css`, `layout.html` + ALL template/admin HTML files (~15) | 0 |
| 10.4D-2: Admin Responsive | `_tokens.css`, `design-tokens.css` + 6 admin HTML files | 0 |
| 10.4D-3: Badge Accent | `_tokens.css`, `design-tokens.css`, `collection.html` | 0 |
| 10.4D-4: Navigation | `index.html`, `collection.html` | 0 |

---

## 8. Execution Order

```
10.4D-1: Type Scale Token         (_tokens.css + all pages)
10.4D-2: Admin Responsive         (_tokens.css + 6 admin)
10.4D-3: Badge Accent Variant     (_tokens.css + collection.html)
10.4D-4: Navigation Link Audit    (index.html)
```

Each phase is independent — can be executed and verified in isolation.

---

## 9. Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| 13px→14px breaks layout | Low | Medium | 1px increase; system-ui font renders 14px ≈ same width as 13px |
| Admin responsive breaks desktop | Low | High | Desktop-first; mobile rules are additive only |
| Table horizontal scroll UX poor | Medium | Low | Users expect scroll on mobile; standard pattern |
| Badge accent overused | Low | Low | Only valid use case is brand/hero badge |

---

> **Document version**: v1.0
> **Status**: FROZEN — awaiting confirmation
> **Next**: Phase 10.4D-1 Type Scale Token

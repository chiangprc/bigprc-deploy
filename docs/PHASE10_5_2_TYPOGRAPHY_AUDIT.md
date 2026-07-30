# Phase 10.5-2 — Typography Audit Report

> Step: Audit only. No code changes.

## 1. Summary

```
Total font-size instances: ~145
  Already using Token:     ~41 (28%)  ✅
  Needs migration:         ~90 (62%)  🔴
  Acceptable exceptions:   ~14 (10%)  🟢  (print media, 15px input, 48px display)
```

## 2. By Size — Recommended Migration

| Current | Count | → Token | Rationale |
|---------|-------|---------|-----------|
| 10px | 1 | `11px` (`--text-caption`) | Footnote — bump to caption |
| 11px | 12 | `var(--text-caption)` | th, labels, captions — exact match |
| 12px | 35 | `var(--text-meta)` | Tags, pills, meta, footer — exact match |
| 13px | 3 | `13px` (table exception) | Table data — needs density; keep 13px |
| 14px | 18 | `var(--text-body)` | Body, subtitle, card title — exact match |
| 15px | 1 | `15px` (input exception) | Search input — form element, keep |
| 16px | 4 | `var(--text-subtitle)` | Section h2 — exact match |
| 18px | 3 | `var(--text-section)` | FAQ h2, theme h2 — exact match |
| 22px | 4 | `var(--text-title)` | Page h1 — exact match |
| 24px | 2 | `var(--text-title)` | H1, stat — reduce 2px |
| 26px | 1 | `22px` keep as exception | Hero stat number — unique context |
| 28px | 3 | `var(--text-title)` | Mobile h1, stat — reduce 6px |
| 32px | 2 | `var(--text-hero)` | Hero h1 — exact match |
| 36px | 1 | `var(--text-hero)` | Index hero — reduce 4px |
| 48px | 2 | `var(--text-display)` | Countdown, empty state — exact match |

## 3. By File — Detailed Audit

### 3.1 `layout.html` — Base Template

| Line | Current | Context | → Token | Risk |
|------|---------|---------|---------|------|
| 79 | `14px` | Topbar nav links | `var(--text-body)` | Low |
| 90 | `12px` | Footer text | `var(--text-meta)` | Low |
| 103 | `12pt` | Print body | keep (print) | — |
| 107 | `0.85em` | Print URL | keep (print) | — |
| 109 | `18pt` | Print h1 | keep (print) | — |

### 3.2 `collection.html` — Collection Detail

| Line | Current | Context | → Token | Risk |
|------|---------|---------|---------|------|
| 18 | `32px` | Hero h1 | `var(--text-hero)` | Low |
| 19 | `16px` | Hero desc | `var(--text-subtitle)` | Low |
| 22 | `26px` | Stat number | keep (unique) | — |
| 23 | `12px` | Stat label | `var(--text-meta)` | Low |
| 34 | `12px` | hl-card text | `var(--text-meta)` | Low |
| 38 | `14px` | Search input | `var(--text-body)` | Low |
| 46 | `14px` | Ed note text | `var(--text-body)` | Low |
| 49 | `14px` | Spotlight title | `var(--text-body)` | Low |
| 51 | `14px` | Related title | `var(--text-body)` | Low |
| 53 | `12px` | Filter label | `var(--text-meta)` | Low |
| 54 | `11px` | Filter count | `var(--text-caption)` | Low |
| 59 | `12px` | Filter pill | `var(--text-meta)` | Low |
| 65 | `12px` | Table h3 .n | `var(--text-meta)` | Low |
| 66 | `13px` | Table body | keep `13px` | — |
| 67 | `11px` | Table th | `var(--text-caption)` | Low |
| 78 | `12px` | Pagination btn | `var(--text-meta)` | Low |
| 81 | `12px` | Pagination info | `var(--text-meta)` | Low |
| 85 | `18px` | FAQ h2 | `var(--text-section)` | Low |
| 88 | `14px` | FAQ summary | `var(--text-body)` | Low |
| 94 | `12px` | Pill link | `var(--text-meta)` | Low |
| 99 | `14px` | Footer link | `var(--text-body)` | Low |
| 103 | `24px` | Mobile hero h1 | `var(--text-title)` | Low |
| 104 | `14px` | Mobile hero desc | `var(--text-body)` | Low |

### 3.3 `collection_index.html` — Collection Index

| Line | Current | Context | → Token | Risk |
|------|---------|---------|---------|------|
| 8 | `24px` | Page h1 | `var(--text-title)` | Low |
| 9 | `14px` | Subtitle | `var(--text-body)` | Low |
| 11 | `18px` | Theme h2 | `var(--text-section)` | Low |
| 16 | `12px` | Card intro | `var(--text-meta)` → `var(--text-body)` | Medium — increases density |
| 17 | `12px` | Card count | `var(--text-meta)` | Low |
| 19 | `14px` | Footer link | `var(--text-body)` | Low |

### 3.4 `detail.html` — Resource Detail

| Line | Current | Context | → Token | Risk |
|------|---------|---------|---------|------|
| 8 | `22px` | Page h1 | `var(--text-title)` | Low |
| 16 | `11px` | Info label | `var(--text-caption)` | Low |
| 26 | `14px` | Desc box | `var(--text-body)` | Low |
| 29 | `11px` | AI disclaimer | `var(--text-caption)` | Low |
| 31 | `12px` | Feedback row | `var(--text-meta)` | Low |
| 35 | `14px` | Related h3 | `var(--text-body)` | Low |
| 46 | `18px` | Mobile h1 | `var(--text-section)` | Low |
| 47 | `14px` | Mobile CTA | `var(--text-body)` | Low |
| 81,88,89,95 | `12px` | Inline notes | `var(--text-meta)` | Low |
| 114 | `11px` | Count span | `var(--text-caption)` | Low |

### 3.5 `list.html` — Resource List

| Line | Current | Context | → Token | Risk |
|------|---------|---------|---------|------|
| 9 | `22px` | Page h1 | `var(--text-title)` | Low |
| 14 | `12px` | Filter tags | `var(--text-meta)` | Low |
| 24 | `14px` | Search input | `var(--text-body)` | Low |
| 31 | `12px` | Table th | `var(--text-meta)` | Low |
| 33 | `13px` | Table td | keep `13px` | — |
| 53 | `12px` | Mobile table | `var(--text-meta)` | Low |
| 56 | `14px` | Mobile btn | `var(--text-body)` | Low |
| 57 | `16px` | Mobile search | `var(--text-subtitle)` | Low |
| 58 | `14px` | Mobile jump | `var(--text-body)` | Low |

### 3.6 `index.html` — Homepage

| Line | Current | Context | → Token | Risk |
|------|---------|---------|---------|------|
| 89 | `14px` | Nav links | `var(--text-body)` | Low |
| 100 | `36px` | Hero h1 | `var(--text-hero)` | Medium — visual impact |
| 101 | `14px` | Subtitle | `var(--text-body)` | Low |
| 107 | `15px` | Search input | keep `15px` | — |
| 115 | `14px` | Cancel btn | `var(--text-body)` | Low |
| 135 | `14px` | Result name | `var(--text-body)` | Low |
| 136 | `12px` | Result meta | `var(--text-meta)` | Low |
| 141 | `12px` | Tag cloud | `var(--text-meta)` | Low |
| 148 | `14px` | Card title | `var(--text-body)` | Low |
| 149 | `12px` | Card subtitle | `var(--text-meta)` | Low |
| 150 | `12px` | Card action | `var(--text-meta)` | Low |
| 162 | `12px` | Product desc | `var(--text-meta)` | Low |
| 164 | `11px` | Disclaimer | `var(--text-caption)` | Low |
| 165 | `12px` | Footer | `var(--text-meta)` | Low |
| 171 | `28px` | Mobile h1 | `var(--text-title)` | Low |
| 219 | `14px` | Noscript link | `var(--text-body)` | Low |
| 231 | `12px` | Product link | `var(--text-meta)` | Low |

### 3.7 Admin Pages — Summary

| File | Hardcoded | Needs Migration |
|------|----------|----------------|
| `dashboard.html` | 3 (`32px`, `12px`, `16px`) | 3 (stat n, card l, section h2) |
| `collections.html` | 2 (`13px`, `11px`) | 2 (table, th) |
| `collection-review.html` | 8 (`22px`, `28px`, `12px`×4, `11px`×2) | 8 |
| `collection-detail.html` | 12 (`22px`, `24px`, `12px`×3, `14px`×3, `48px`, `18px`, `11px`×3, `10px`) | 12 |
| `editorial.html` | 4 (`28px`, `12px`, `16px`, `13px`, `11px`×2, `14px`) | 6 |
| `editorial-detail.html` | 4 (`22px`, `14px`×3, `12px`) | 5 |

## 4. Non-Scale Sizes — Special Handling

| Size | Context | Recommendation |
|------|---------|---------------|
| `10px` | Footnote in collection-detail | Bump to `11px` (`--text-caption`) |
| `13px` | Table data (collection, list, editorial) | **Keep 13px** — density requirement for data tables |
| `15px` | Search input (index.html) | **Keep 15px** — form element, not typography |
| `24px` | Stat numbers, h1 | Reduce to `22px` (`--text-title`) |
| `26px` | Hero stat (collection.html) | **Keep 26px** — unique display context |
| `28px` | Stat numbers, mobile h1 | Reduce to `22px` (`--text-title`) |
| `36px` | Hero h1 (index.html) | Reduce to `32px` (`--text-hero`) |

## 5. Migration Priority

| Priority | Scope | Files | Instances |
|----------|-------|-------|-----------|
| 🔴 P0 | `12px → var(--text-meta)` | All 13 files | 35 |
| 🔴 P0 | `14px → var(--text-body)` | All 13 files | 18 |
| 🟡 P1 | `11px → var(--text-caption)` | 6 files | 12 |
| 🟡 P1 | `16px → var(--text-subtitle)` | 3 files | 4 |
| 🟡 P1 | `18px → var(--text-section)` | 2 files | 3 |
| 🟡 P1 | `22px → var(--text-title)` | 4 files | 4 |
| 🟢 P2 | `24/28/32/36px → token` | 4 files | 7 |

## 6. Risk Assessment

| Risk | Detail | Mitigation |
|------|--------|------------|
| 12px→12px token | No visual change at all | Safe bulk replace |
| 14px→14px token | No visual change at all | Safe bulk replace |
| 24→22px | Minor reduction in stat/h1 size | Acceptable — within tolerance |
| 28→22px | Noticeable reduction in stat size | Designer review recommended |
| 36→32px | Hero h1 reduction on homepage | Designer review recommended |
| Card intro 12→14px | Increased density in card list | Improves readability; intentional |

---

> **Status: AUDIT COMPLETE — ~145 instances audited across 13 files.**
> **~90 migrations identified. Awaiting confirmation to proceed.**

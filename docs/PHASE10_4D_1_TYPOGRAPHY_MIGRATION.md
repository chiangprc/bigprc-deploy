# Phase 10.4D-1 — Typography Migration Report

## Type Scale Tokens Added

```
--text-caption:  11px   (badge, error footnote)
--text-meta:     12px   (tag, table cell, filter pill)
--text-body:     14px   (paragraph, label, nav link — migrated from 13px)
--text-subtitle: 16px   (section desc, card title — migrated from 15px)
--text-section:  18px   (h2, faq title, admin h1 — migrated from 20px)
--text-title:    22px   (page h1 detail/list/collection)
--text-hero:     32px   (hero h1 collection)
--text-display:  48px   (countdown, empty state)
```

## Migration Statistics

| Size | Before | After | Delta | Files Affected |
|------|--------|-------|-------|---------------|
| 13px | ~50 | 0 | → `var(--text-body)` = 14px (+1) | 11 files |
| 15px | 7 | 1 (search input) | → `var(--text-subtitle)` = 16px (+1) | 4 files |
| 20px | 7 | 0 | → `var(--text-section)` = 18px (-2) | 4 files |

## Files Modified

| File | 13px → body | 15px → subtitle | 20px → section |
|------|------------|-----------------|-----------------|
| `_tokens.css` | — | — | — (token source) |
| `design-tokens.css` | — | — | — (synced) |
| `index.html` | 4 | 1 | 0 |
| `collection.html` | 3 | 2 | 0 |
| `collection_index.html` | 0 | 1 | 0 |
| `detail.html` | 4 | 0 | 0 |
| `list.html` | 4 | 0 | 0 |
| `transit.html` | 1 | 0 | 0 |
| `dashboard.html` | 3 | 0 | 1 |
| `collections.html` | 3 | 0 | 1 |
| `collection-review.html` | 2 | 1 | 0 |
| `collection-detail.html` | 15 | 1 | 4 |
| `editorial.html` | 3 | 0 | 1 |
| `editorial-detail.html` | 3 | 0 | 0 |

## Scope Exclusions

- `font-size:15px` on index.html search input — kept (form element, not typography)
- `claudeek.html` — 8 × 13px, 2 × 15px, 1 × 20px (out of scope)
- `404.html` — 2 × 13px, 1 × 20px (out of scope)

## Visual Risk Assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| 13px→14px | Low | 1px increase; system-ui renders 14px at virtually same width |
| 15px→16px | Low | Section titles gain 1px — improves readability |
| 20px→18px | Low | Admin h1 reduces 2px — still clearly larger than body (14px) |

## Typography Class Decision

No `.text-*` utility classes created. Existing components (`.badge`, `.tag`, `.btn`, `.card`) already define their own font-sizes via component CSS. Adding utility classes would create two ways to set font-size.

## Verification

```
Scope 13px: 0  ✅
Scope 15px: 1  ✅ (search input — intentional keep)
Scope 20px: 0  ✅
Token usage: 54 instances across 12 files
```

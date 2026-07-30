# Phase 10.6-1 — Typography Refinement Report

## Part A: P1 Fixes Executed

| Fix | Before | After | Instances |
|-----|--------|-------|-----------|
| 11px → --text-caption | hardcoded | token | 16 |
| Section H2 → --text-section | 16px | token (18px) | 2 (dashboard, editorial) |
| Stat numbers → --text-hero | 24/28/32px | token (32px) | 4 (dashboard, review, detail, editorial) |
| 22px → --text-title | hardcoded | token | 4 (detail, list, review, detail, ed-detail) |
| 32px → --text-hero | hardcoded | token | 1 (collection hero) |
| 48px → --text-display | hardcoded | token | 2 (transit, collection-detail) |

**Total: 29 instances migrated. 0 P1 remaining.**

---

## Part B: Type Scale Refinement Proposal

### Current Scale

```
--text-caption:  11px
--text-meta:     12px
--text-body:     14px
--text-subtitle: 16px
--text-section:  18px
--text-title:    22px
--text-hero:     32px
--text-display:  48px
```

### Assessment

The current scale creates a "marketing landing page" feel at the upper range. Compared to Stripe/Linear/Notion:

| Level | BigPRC | Stripe | Linear | Notion |
|-------|--------|--------|--------|--------|
| Body | 14px | 13px | 13px | 14px |
| Subtitle/Card Title | 16px | 14px | 14px | 14px |
| Section | 18px | 16px | 14px | 16px |
| Page Title | 22px | 20px | 20px | 30px* |
| Hero | 32px | — | — | 30px |

*Notion page title is a document title, not a UI page title.

BigPRC is **1-2px larger at every level** compared to the reference products. For a Chinese editorial site, some extra size is justified (Chinese characters are denser), but the current gap is noticeable.

### Proposed Refined Scale

```
Token            Current   Proposed   Delta   Rationale
─────────────────────────────────────────────────────────
--text-caption    11px      11px       —       Already minimal
--text-meta       12px      12px       —       Already refined
--text-body       14px      14px       —       Chinese readability preserved
--text-subtitle   16px      15px       -1      Reduce marketing feel
--text-section    18px      18px       —       Section headers need presence
--text-title      22px      20px       -2      Noticeable refinement
--text-hero       32px      28px       -4      Editorial, not marketing
--text-display    48px      48px       —       Countdown preserved
```

**Only 3 tokens change**: subtitle -1, title -2, hero -4.

### Why this specific set

**Keep body at 14px**: Chinese text at 13px is standard for apps like WeChat, but BigPRC is an editorial reading experience. 14px body text signals "this is meant to be read" — like Medium or Apple News. Reducing to 13px would trade comfort for density.

**Reduce hero by 4px**: 32px → 28px is the biggest single change. 32px hero text says "marketing page." 28px says "editorial publication." This is the difference between "BIGPRC" and "BigPRC" — the former shouts, the latter speaks.

**Reduce title by 2px**: 22px → 20px. Page titles (H1) currently feel slightly overbearing on list/detail pages. At 20px, they remain clearly hierarchical above section headers (18px) and body (14px), but with more restraint.

**Reduce subtitle by 1px**: 16px → 15px. Card titles and subtitles. This is a micro-adjustment — barely perceptible, but contributes to the overall refined feel.

### Hierarchy Preservation

```
Proposed hierarchy gap:
  hero (28) → title (20): 8px gap ✅
  title (20) → section (18): 2px gap ⚠️ tight
  section (18) → subtitle (15): 3px gap ✅
  subtitle (15) → body (14): 1px gap ⚠️ very tight
  body (14) → meta (12): 2px gap ✅
  meta (12) → caption (11): 1px gap ✅
```

The `title→section` (2px) and `subtitle→body` (1px) gaps are tight. This is acceptable because:
- Title and section rarely appear on the same page (title is page H1, section is content H2)
- Subtitle and body are differentiated by weight (600 vs 400) + color, not just size

### Impact Assessment

| Page | Element | Before | After | Visual Change |
|------|---------|--------|-------|---------------|
| index.html | Hero H1 | 36px* | 32px* | -4px (noticeable) |
| collection.html | Hero H1 | 32px | 28px | -4px (refined) |
| list/detail | Page H1 | 22px | 20px | -2px (subtle) |
| collection_index | Card title | 16px | 15px | -1px (barely visible) |
| Admin pages | Page H1 | 18-22px | 18-20px | 0 to -2px |

*index.html hero uses 36px hardcoded. After migration to --text-hero, it becomes 28px.

### Risk

| Risk | Mitigation |
|------|------------|
| Title→Section gap too close (2px) | They never appear adjacent on same page |
| 15px is not a "round" number | 15px is widely used in UI (iOS system font sizes include 15px) |
| index.html hero 36→28 feels small | The hero copy is only 4 characters — "发现好工具" — 28px is still prominent |

---

## Recommendation

**Proceed with the 3-token refinement** (subtitle -1, title -2, hero -4). Body, section, meta, caption, display unchanged.

Impact: 3 tokens change, ~30 references cascade. All existing CSS rules using `var(--text-*)` update automatically.

---

> **Status: P1 fixes DONE. Type Scale proposal awaiting confirmation.**

# Phase 10.4D-2 — Admin Responsive Foundation

## Architecture

```
_tokens.css  ←  shared responsive rules (single source)
  └── @media (max-width: 768px)   tablet/mobile
  └── @media (max-width: 480px)   small phone
```

All 6 admin pages inherit responsive behavior from the shared CSS. No per-page responsive patches.

## Breakpoints

| Breakpoint | Target | Behavior |
|------------|--------|----------|
| `> 768px` | Desktop | Default layout (unchanged) |
| `≤ 768px` | Tablet / Mobile | Padding reduced, cards collapse 2-col, tables scroll, actions stack |
| `≤ 480px` | Small phone | Cards collapse 1-col |

## Responsive Rules

### Container
```css
.wrap { padding: var(--space-lg) var(--space-md); }
```

### Card Grid
```css
.cards { grid-template-columns: repeat(2, 1fr); }    /* 768px */
.cards { grid-template-columns: 1fr; }                /* 480px */
```

### Table Horizontal Scroll
```css
.table-wrap {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
}
.table-wrap table { min-width: 600px; }
```

### Action Area Stack
```css
.links, .toolbar {
    flex-direction: column;
    align-items: stretch;
}
.links .btn, .toolbar .btn, .toolbar input, .toolbar select {
    width: 100%;
}
```

### Touch Targets
```css
.btn, td a {
    min-height: 44px;
    align-items: center;
    display: inline-flex;
}
```

## Table Wrapper Coverage

| Page | Tables | Wrapped |
|------|--------|---------|
| dashboard | 0 | N/A |
| collections | 1 | ✅ `.table-wrap` |
| collection-review | 1 (sample) | ✅ `.table-wrap` |
| collection-detail | 2 (shared + samples) | ✅ `.table-wrap` |
| editorial | 1 (8-column status) | ✅ `.table-wrap` |
| editorial-detail | 0 | N/A |

## Files Modified

| File | Change |
|------|--------|
| `_tokens.css` | +30 lines responsive rules (single source) |
| `design-tokens.css` | Synced |
| `collections.html` | +1 `.table-wrap` wrapper |
| `collection-review.html` | +1 `.table-wrap` wrapper |
| `collection-detail.html` | +2 `.table-wrap` wrappers |
| `editorial.html` | +1 `.table-wrap` wrapper |

## Verification Recommendations

Test on real devices / devtools:
1. Open each admin page at 375px viewport
2. Verify tables scroll horizontally (no data loss)
3. Verify card grids collapse to 2 columns → 1 column
4. Verify buttons/inputs are full-width and touchable
5. Verify no horizontal page scroll beyond viewport

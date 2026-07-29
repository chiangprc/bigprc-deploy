# Phase 10.4 — BigPRC Design System Proposal

> **Status**: Architecture Review  
> **Scope**: Frontend + Admin, all pages  

---

## 1. Problems Identified

| # | Problem | Location | Severity |
|---|---------|----------|----------|
| 1 | Card border-radius varies: 6px, 8px, 10px, 14px | collection, admin, index | High |
| 2 | Left accent border (3px solid) on featured cards feels heavy | collection_index, admin | Medium |
| 3 | Spotlight cards had no hover/background (fixed in 10.3) | collection.html | Resolved |
| 4 | Emoji icons look informal on a curation platform | Entire site | Medium |
| 5 | No shared CSS — every page has its own inline styles | All 6 admin pages | High |
| 6 | Color palette expanded organically: --accent, --primary, --cta, --red, --amber, --blue | All pages | Low |

---

## 2. Design Principles

1. **One card, one style.** All cards across the site share the same visual language.
2. **Remove, don't add.** Delete left accent borders. Simplify borders. Reduce visual noise.
3. **Icons over emoji.** Replace emoji with lightweight SVG icons for a more polished look.
4. **Calm editorial tone.** Fewer colors. Consistent spacing. Let content breathe.

---

## 3. Card System

### Single Card Definition

```css
.card {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px 24px;
    background: var(--card-bg);
    transition: border-color 0.15s, box-shadow 0.15s;
}
.card:hover {
    border-color: var(--accent);
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
```

### Variants (via modifier classes)

```css
.card--featured { border-color: var(--accent); }  /* subtle, not 3px left bar */
.card--compact  { padding: 14px 18px; }           /* admin lists */
.card--clickable { cursor: pointer; }              /* link cards */
```

### What to Remove

| Current | Replacement |
|---------|-------------|
| `.coll-card.featured` with `border-left: 3px solid` | `.card--featured` with subtle full-border accent |
| Inline spotlight card styles | `.card .card--clickable` |
| `.ed-card` (editorial card — 10px radius) | `.card` (8px radius, unified) |
| `.hl-card` (highlight card — 8px radius) | `.card` |

### Migration: 6 card CSS classes → 1 `.card` + 3 modifiers

---

## 4. Button System

| Variant | Use | Style |
|---------|-----|-------|
| `.btn-primary` | Primary action (rare — search, CTA) | `background: var(--accent); color: #fff; border-radius: 6px; padding: 10px 20px` |
| `.btn-ghost` | Navigation, secondary actions | `border: 1px solid var(--border); color: var(--text); border-radius: 6px; padding: 8px 16px` |
| `.btn-text` | Inline links | `color: var(--accent); text-decoration: none` |

**Implementation**: Small. Most buttons are already inline `<a>` tags styled per-page. Consolidation is CSS-class-level only.

---

## 5. Tag/Badge System

| Variant | Use | Style |
|---------|-----|-------|
| `.tag` | Category, topic | `border: 1px solid var(--border); border-radius: 12px; padding: 2px 10px; font-size: 11px` |
| `.badge` | Status (published, draft, CORE) | `border-radius: 10px; padding: 3px 12px; font-size: 11px; font-weight: 500` |
| `.badge--success` | Published, stable | `background: var(--accent-soft); color: var(--accent)` |
| `.badge--warning` | Draft, warning | `background: var(--amber-soft); color: var(--amber)` |
| `.badge--danger` | Rejected, unstable | `background: var(--red-soft); color: var(--red)` |

---

## 6. Icon System

### Recommendation: Lucide Icons

| Criteria | Lucide | Heroicons | Tabler |
|----------|--------|-----------|--------|
| Icon count | 1,400+ | 300+ | 4,000+ |
| SVG quality | Consistent 24px grid | Excellent | Varies |
| Bundle size (tree-shaken) | ~3KB per icon | ~2KB | ~4KB |
| Editorial feel | Clean, minimal | More technical | More UI-kit |
| License | ISC (free) | MIT (free) | MIT (free) |

**Recommend Lucide.** Clean, minimal, editorial feel. Consistent 24px × 24px stroke-based design.

### Emoji → Icon Mapping

| Current Emoji | Replacement (Lucide) | Location |
|---------------|---------------------|----------|
| 🌟 | `star` | Spotlight section |
| 📝 | `pen-line` | Editorial section |
| 📚 | `library` | Collection index |
| 🛠 | `wrench` | Collection index |
| 🎓 | `graduation-cap` | Collection index |
| 🌍 | `globe` | Collection index |
| 🔗 | `link` | Related collections |
| ⭐ | `bookmark` | Featured |
| 👥 | `users` | Audience |
| 💬 | `message-circle` | FAQ |
| 🔍 | `search` | Other collections |
| ✅ | `check-circle` | Publish status |
| 🟢🟡🔴⚪ | `circle` (filled) | Status dots |

### Implementation Strategy

1. Add Lucide CDN script (one `<script>` tag in `layout.html`)
2. Replace emoji with `<i data-lucide="star"></i>` elements
3. Lucide auto-replaces on ` lucide.createIcons()`
4. Admin pages: same approach, add CDN to each page

**No npm. No build step. CDN only.** 11KB gzipped for full library, or ~2KB per page with tree-shaking via CDN params.

---

## 7. Typography

| Level | Size | Weight | Use |
|-------|------|--------|-----|
| H1 | 28px | 800 | Page hero titles |
| H2 | 18px | 700 | Section headers |
| H3 | 15px | 600 | Card titles |
| Body | 14px | 400 | Paragraph text |
| Meta | 12px | 400 | Secondary info, counts |
| Caption | 11px | 400 | Badges, tags, footnotes |

**Font**: `system-ui, -apple-system, sans-serif` (already in use). No web font. No performance cost.

---

## 8. Spacing Scale

```
4px   — tight (icon gaps, badge padding)
8px   — compact (card gaps, inline spacing)
12px  — default (section padding, card grid gap)
16px  — relaxed (section margins)
24px  — wide (page section gaps)
32px  — hero spacing
```

---

## 9. Color

### Keep: current `--bg`, `--text`, `--secondary`, `--border`, `--primary`, `--card-bg`

### Add: semantic tokens (map to existing values)

```css
--accent:        #1a6b4f;    /* primary action, featured */
--accent-soft:   #e8f5e9;    /* badge background */
--amber:         #f0a030;    /* warning */
--amber-soft:    #fef9f0;    /* warning background */
--red:           #c0392b;    /* danger */
--red-soft:      #fde8e8;    /* danger background */

/* Dark mode overrides already exist for all of the above */
```

### Remove: unused `--cta`, `--blue`, `--warn`, `--warn-soft` (consolidate into amber/red)

---

## 10. Implementation Phases

### Phase 10.4A — Card Unification (~2h)

- Define `.card` + modifiers in `layout.html` `<style>`
- Replace `.coll-card`, `.ed-card`, `.hl-card`, spotlight inline styles with `.card`
- Remove left accent borders, replace with `.card--featured`
- Scope: 4 templates (collection.html, collection_index.html, detail.html, list.html)

### Phase 10.4B — Admin Card Cleanup (~1h)

- Replace admin page inline card styles with `.card` where applicable
- Scope: dashboard.html, collections.html, editorial.html, collection-review.html, collection-detail.html, editorial-detail.html

### Phase 10.4C — Icon Migration (~1h)

- Add Lucide CDN to `layout.html`
- Replace emoji with Lucide icons on frontend pages
- Replace status dot emoji with Lucide `circle` icons on admin pages
- Scope: all templates

### Phase 10.4D — Color Consolidation (~30min)

- Remove unused CSS variables
- Standardize badge colors across admin pages
- Scope: layout.html, admin pages

---

## 11. What Does NOT Change

- HTML semantics (all `<a>`, `<section>`, `<article>` tags preserved)
- SEO fields (title, description, canonical, OG, schema)
- Static generation pipeline
- Jinja2 template structure
- Admin page architecture
- JavaScript behavior
- Database schema

---

## 12. Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Card unification breaks existing hover effects | `.card:hover` matches old behavior |
| Lucide CDN fails to load | Icons fall back to text labels (already present as emoji fallback) |
| Dark mode contrast issues | All color variables already have dark mode definitions |
| Admin pages look broken after card change | Minimal change — only swapping CSS classes, not HTML structure |

---

确认后从 Phase 10.4A 开始。
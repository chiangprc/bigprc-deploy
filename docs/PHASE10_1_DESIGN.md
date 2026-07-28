# Phase 10.1 — Collection Page UX Enhancement Design

> **Status**: Design  
> **Depends on**: v0.9.5-stable (Editorial Publish)  

---

## 1. Current State

```
/collection/bbc-nature.html

  Hero: title + intro + count
  Editorial cards ({% if editorial_status == 'published' %})
    ├── 📝 编辑推荐 (editor_note)
    ├── ⭐ 为什么值得收藏 (why_collect)
    └── 👥 适合人群 (audience)
  Resource table (315 rows, paginated)
  FAQ
  Related collections
```

**Problem**: Editorial cards are full-width, multi-card blocks that push the resource table far down the page. Users must scroll past ~800px of editorial content to reach resources.

---

## 2. Target State

```
/collection/bbc-nature.html

  Hero: title + intro + count
  
  ── 编辑推荐 ── (compact, single row)
  editor_note (2-3 lines max, truncated) · why_collect · audience
  [⬇ 查看全部资源]

  ── 快速筛选 ── (category tag pills, static)
  [自然科学] [BBC] [海洋] [动物] [宇宙]
  共 315 个资源
  
  ── 精选 ── (Phase 10.2 placeholder, hidden now)
  {% if spotlight %}...

  Resource table (paginated)
  FAQ
  Related collections
```

### Layout Flow

```
Hero (80px)
  ↓
Editorial Compact (60px) ← NEW, replaces multi-card editorial section
  ↓
Quick Filter (40px) ← NEW, category tag pills
  ↓
Resource Table (pagination)
  ↓
FAQ
  ↓
Related Collections
```

---

## 3. Data Source

| Component | Source | Already Available? |
|-----------|--------|-------------------|
| editor_note | `collection_content` | ✅ Passed in template |
| why_collect | `collection_content` | ✅ |
| audience | `collection_content` | ✅ |
| editorial_status | `collection_content` | ✅ Added in Phase 9.4B |
| Category tags | Resource rows' `category` field | ✅ Already in resource loop |
| Spotlight | `resource_collections.spotlight` | ❌ Not yet (Phase 10.2) |

**No new data needed.** All fields already flow through `auto_generate.py` → `collection.html` template.

---

## 4. Template Changes

### `collection.html`

#### A. Editorial Compact (replace multi-card editorial section)

Current:
```jinja
{% if editorial_status == 'published' and (editor_note or why_collect or audience) %}
<section class="ed">
    {% if editor_note %}<div class="ed-card">...</div>{% endif %}
    {% if why_collect %}<div class="ed-card">...</div>{% endif %}
    {% if audience %}<div class="ed-card">...</div>{% endif %}
</section>
{% endif %}
```

New:
```jinja
{% if editorial_status == 'published' and editor_note %}
<section class="ed-compact">
    <div class="ed-compact-text">{{ editor_note[:120] }}{% if editor_note|length > 120 %}...{% endif %}</div>
    {% if why_collect %}<span class="ed-tag">{{ why_collect }}</span>{% endif %}
    {% if audience %}<span class="ed-tag">{{ audience }}</span>{% endif %}
</section>
{% endif %}
```

**Design intent**: One compact row instead of 3 full cards. Truncated editor_note (120 chars). why_collect + audience as small tag badges. User sees the editorial judgment at a glance, then scrolls to resources.

#### B. Quick Filter (category pills)

```jinja
{% set categories = resources | map(attribute='category') | reject('eq', None) | reject('eq', '') | unique | list %}
{% if categories|length > 1 %}
<section class="qf">
    <span class="qf-label">筛选:</span>
    {% for cat in categories[:8] %}
    <span class="qf-pill" onclick="F('{{ cat }}')">{{ cat }}</span>
    {% endfor %}
    <span class="qf-count">{{ resources|length }} 个资源</span>
</section>
{% endif %}
```

**Static generation**: Category list computed in Jinja2 at render time. Filter interaction is JS only (show/hide table rows by category). No backend.

#### C. Spotlight Placeholder

```jinja
{% if spotlight_resources %}
<section class="spotlight">
    <h2>精选</h2>
    {% for r in spotlight_resources %}
    <a href="/go/{{ r.res_id }}" class="spotlight-card">{{ r.title }}</a>
    {% endfor %}
</section>
{% endif %}
```

Empty for now. `spotlight_resources` passed as empty list from `auto_generate.py`. Phase 10.2 will populate it.

---

## 5. CSS Changes

| Class | Purpose |
|-------|---------|
| `.ed-compact` | Compact editorial row (replaces `.ed` card grid) |
| `.ed-compact-text` | Truncated editor_note (2-3 lines max-height) |
| `.ed-tag` | Inline badge for why_collect / audience |
| `.qf` | Quick filter bar |
| `.qf-pill` | Category filter tag |
| `.spotlight` | Placeholder section (Phase 10.2) |

---

## 6. auto_generate.py Changes

Pass `spotlight_resources=[]` (empty list) to template. Phase 10.2 will query `resource_collections WHERE spotlight=1`.

---

## 7. Risk Analysis

| Risk | Mitigation |
|------|-----------|
| Jinja2 `map(attribute='category')` fails on None values | `| reject('eq', None)` filter |
| Editorial compact hides too much | Truncation at 120 chars preserves key judgment. Full text on editorial-detail page for admin. |
| Category filter JS not accessible to crawlers | All resources still in static HTML table. Filter is progressive enhancement only. |
| Existing collections without editorial_status | `COALESCE(editorial_status, 'draft')` in auto_generate.py SELECT |

---

## 8. Files

| File | Change | Lines |
|------|--------|-------|
| `collection.html` | Editorial compact + quick filter + spotlight placeholder | +30/-25 |
| `auto_generate.py` | Pass `spotlight_resources=[]` | +2 |

**Total: ~32 lines. Zero migrations. Zero schema changes. Zero pipeline changes.**

---

## 9. Acceptance Criteria

- [ ] Published collections show editorial compact (not multi-card)
- [ ] Draft/reviewed/approved collections show NO editorial content (gate works)
- [ ] Category filter pills render with correct counts
- [ ] 16 collection pages all generate without errors
- [ ] SEO title/canonical/sitemap unchanged
- [ ] Phase 10.2 spotlight block has empty `<section>` ready for content

---

确认后编码。
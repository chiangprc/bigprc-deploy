# Phase 10 — User-Facing Curation Roadmap

> **Status**: Proposal  
> **Depends on**: v0.9.5-stable (Editorial Publish)  

---

## Principle

Phase 1-9 built the engine. Phase 10 makes the product feel curated.

Every feature must answer: **"Does this help a user discover, judge, and choose a resource?"**

---

## Phase 10.1 — Collection Page Quality

**Goal**: Collection pages feel like curated guides, not resource lists.

### Current State

```
/collection/bbc-nature.html

  Hero: title + intro + count
  Editorial cards (hidden until published)
  Resource table (315 rows, paginated)
  FAQ
  Related collections
```

### Target State

```
/collection/bbc-nature.html

  Hero: title + intro + count + editorial_note (if published)
  ── 编辑推荐 ──
  editorial content (compact card)
  
  ── 从这里开始 ──    ← NEW: spotlight 3-5 resources
  《蓝色星球》海洋纪录片标杆 · 《地球脉动》全球生态奇观 · 《绿色星球》植物视角

  ── 快速筛选 ──        ← NEW: category/tag filter pills
  [自然科学] [BBC] [海洋] [动物] [宇宙]

  ── 全部资源 (315) ──
  table (existing, keep)
  
  FAQ
  Related collections
```

| Component | Data Source | Change |
|-----------|-----------|--------|
| Spotlight row | `resource_collections` WHERE `spotlight=1` LIMIT 5 | +1 column |
| Category filter pills | Categories from resource rows (already in data) | JS only |
| Editorial compact | `editor_note` (already in template) | CSS only |

**Files**: `collection.html` (+30), `auto_generate.py` (+3 for spotlight), migration 018 (+1 column)

---

## Phase 10.2 — Resource Spotlight

**Goal**: Editor can mark 3-5 standout resources per collection. Frontend highlights them.

### Data

```sql
-- Migration 018
ALTER TABLE resource_collections ADD COLUMN spotlight INTEGER DEFAULT 0;
```

### CLI

```bash
# Mark spotlight
python3 collection_curate.py --spotlight bbc-nature p001

# Unmark
python3 collection_curate.py --unspotlight bbc-nature p001

# List spotlight resources
python3 collection_curate.py --list bbc-nature
```

### Frontend

Spotlight resources appear as cards at the top of the collection page, above the resource table. Each card: title + category + link.

**Files**: `collection_curate.py` (~60), migration 018 (+1), `auto_generate.py` (+5), `collection.html` (+15)

---

## Phase 10.3 — Collection Discovery UX

**Goal**: `/collection/index.html` helps users browse collections by theme.

### Current: flat card grid

### Target: themed sections

```
── 🌍 自然与科学 ──
  BBC 自然纪录片 (315)  ·  Discovery 科学探索 (42)  ·  宇宙探索 (40)

── 📚 文化与经典 ──
  道家经典文献 (41)  ·  道教符箓科仪 (70)  ·  道家手抄孤本 (19)

── 🛠 效率工具 ──
  Android 实用工具 (40)  ·  Windows 效率软件 (12)  ·  AI 效率工具 (12)
```

**Data**: Static grouping defined in `COLLECTION_DEFS` or `collections` table. No schema change — grouping is a display concern.

**Files**: `collection_index.html` (+25), `auto_generate.py` (+10 for grouping data)

---

## Phase 10.4 — Editorial Quality (Admin)

**Goal**: Dashboard shows a quality score for editorial content, helping editors prioritize.

Already partially covered by `editorial.html` (completeness %). Phase 10.4 adds:

- Length check: editor_note < 100 chars → flag
- Freshness: last generated > 30 days → flag

**Files**: `collection_dashboard_export.py` (+10 for quality flags), `editorial.html` (+5 display)

---

## Priority & Impact Matrix

| Phase | User Impact | Dev Cost | Priority |
|-------|-----------|----------|----------|
| 10.1 — Collection Page Quality | ⭐⭐⭐⭐⭐ (every visitor) | ~50 lines | **P0** |
| 10.2 — Resource Spotlight | ⭐⭐⭐⭐ (curated feel) | ~80 lines | **P1** |
| 10.3 — Collection Discovery UX | ⭐⭐⭐ (browsing) | ~35 lines | **P1** |
| 10.4 — Editorial Quality | ⭐⭐ (admin only) | ~15 lines | **P2** |

---

## Migration Impact

| Phase | Migration | Type |
|-------|-----------|------|
| 10.1 | None | — |
| 10.2 | 018 — `resource_collections.spotlight` | Additive, default 0 |
| 10.3 | None | — |
| 10.4 | None | — |

**Total: 1 migration (additive only). Zero schema breakage.**

---

## Recommendation

Start with Phase 10.1 (highest user impact, lowest cost). 10.2 adds editorial curation capability. 10.3-10.4 are polish.

确认后从 10.1 开始。
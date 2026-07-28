# Phase 10.2 — Resource Spotlight Release Notes

> **Tag**: `v0.10.2-stable`  
> **Date**: 2026-07-29  
> **Status**: Frozen  

---

## 1. Release Summary

Phase 10.2 introduces **Resource Spotlight** — editor-curated featured resources within collections. This is a per-relationship property, not a per-resource property. The same resource can be spotlighted in one collection but not another.

### Core Principle

Spotlight is **editorial judgment**, not algorithmic scoring. There are no scores, no rankings, no "top 10" computed lists. The editor decides which resources deserve attention in each collection.

---

## 2. Architecture Decision

### Why `resource_collections.spotlight` (not `resources.spotlight`)?

```
BBC Blue Planet (p001):

  bbc-nature      | p001 | spotlight=1   ← Featured here
  ocean-wildlife  | p001 | spotlight=1   ← Featured here too
  documentary-all | p001 | spotlight=0   ← Not featured here
```

Spotlight is a **relationship property**: "resource X is featured IN collection Y." The same resource appears in multiple collections with independent spotlight decisions per collection. A join table column is the correct relational model.

---

## 3. CLI Usage

```bash
# Mark spotlight
python3 collection_curate.py --spotlight bbc-nature p001

# Remove spotlight
python3 collection_curate.py --unspotlight bbc-nature p001

# List spotlight for a collection
python3 collection_curate.py --list bbc-nature

# List all spotlighted across all collections
python3 collection_curate.py --list-all
```

---

## 4. Data Model

```sql
ALTER TABLE resource_collections ADD COLUMN spotlight INTEGER DEFAULT 0;
```

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `spotlight` | INTEGER | 0 | 0 = normal, 1 = editor spotlighted in this collection |

---

## 5. Frontend

Collection page: spotlight resources displayed as cards above the resource table. Max 5 per collection. Section hidden when no spotlight resources exist.

---

## 6. Verification

```
$ python3 collection_curate.py --spotlight bbc-nature p001
✅ BBC Blue Planet → spotlight in BBC 自然纪录片

$ python3 collection_curate.py --list bbc-nature
  Spotlight: BBC 自然纪录片 (3 resources)
  🌟 p001  BBC Blue Planet
  🌟 p003  BBC Frozen Planet
  🌟 p007  BBC Big Cats

$ python3 auto_generate.py
  → /collection/bbc-nature.html shows 3 spotlight cards
```

---

## 7. Rollback

```bash
# Remove individual spotlight
python3 collection_curate.py --unspotlight bbc-nature p001

# Remove all spotlights
python3 -c "import sqlite3; c=sqlite3.connect('/root/scripts/database.db'); c.execute('UPDATE resource_collections SET spotlight=0'); c.commit()"

# Remove column (SQLite 3.37+)
# ALTER TABLE resource_collections DROP COLUMN spotlight;
```

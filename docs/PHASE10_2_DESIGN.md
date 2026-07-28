# Phase 10.2 — Resource Spotlight Design

> **Status**: Design  
> **Depends on**: v0.10.1-stable (Collection UX)  

---

## 1. Data Model

### Migration 018 — `resource_collections.spotlight`

```sql
ALTER TABLE resource_collections ADD COLUMN spotlight INTEGER DEFAULT 0;
```

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `spotlight` | INTEGER | 0 | 0 = normal, 1 = editor spotlighted in this collection |

**Why `resource_collections` (not `resources` or new table)?**

- Spotlight is a relationship property: "resource X is featured IN collection Y." Same resource can be spotlighted in multiple collections independently. This belongs in the join table.
- Adding to `resources` would make spotlight global — wrong semantics. BBC Blue Planet is a spotlight in BBC Nature but not necessarily in Ocean Wildlife.
- No new table needed. One column. Minimal.

### Impact on existing scripts

| Script | Impact |
|--------|--------|
| `collection_generator.py` | None. `INSERT OR IGNORE` will leave `spotlight=0` (default) |
| `auto_generate.py` | Query `spotlight=1` resources per collection, pass to template |
| `collection_dashboard_export.py` | None. Editorial dashboard reads `collection_content`, not `resource_collections` |

---

## 2. CLI — `collection_curate.py`

### Commands

```bash
# Spotlight a resource in a collection
python3 collection_curate.py --spotlight bbc-nature p001

# Remove spotlight
python3 collection_curate.py --unspotlight bbc-nature p001

# List spotlight resources for a collection
python3 collection_curate.py --list bbc-nature

# List all spotlighted resources across all collections
python3 collection_curate.py --list-all
```

### Output

```
$ python3 collection_curate.py --list bbc-nature

  Spotlight: BBC 自然纪录片 (3 resources)
  🌟 p001  BBC Blue Planet
  🌟 p003  BBC Frozen Planet
  🌟 p007  BBC Big Cats

$ python3 collection_curate.py --spotlight bbc-nature p001

  ✅ BBC Blue Planet → spotlight in BBC 自然纪录片
```

### Safety

- `--spotlight`: `UPDATE resource_collections SET spotlight=1 WHERE resource_id=? AND collection_id=?`. If the resource-collection relationship doesn't exist, prints error.
- `--unspotlight`: Same but SET spotlight=0.
- No audit log needed — spotlight is a lightweight toggle, not a state transition.
- `--dry-run` mode: prints what would happen, no writes.

---

## 3. Frontend — `collection.html`

### Template

The `{% if spotlight_resources %}` block already exists (Phase 10.1 placeholder).

Phase 10.2 populates it:

```jinja
{% if spotlight_resources %}
<section style="padding-bottom:24px">
    <h3 style="font-size:16px;font-weight:700;margin-bottom:10px">🌟 编辑精选</h3>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px">
    {% for r in spotlight_resources %}
        <a href="/go/{{ r.res_id }}" style="display:block;padding:14px 16px;border:1px solid var(--border);border-radius:6px;background:var(--card-bg);text-decoration:none">
            <div style="font-size:13px;font-weight:600;color:var(--text)">{{ r.title }}</div>
            <div style="font-size:11px;color:var(--sec);margin-top:4px">{{ r.category or '' }}</div>
        </a>
    {% endfor %}
    </div>
</section>
{% endif %}
```

### Data Source

`auto_generate.py` queries per collection:

```python
spotlight = cursor.execute("""
    SELECT r.res_id, r.title, r.category
    FROM resources r
    JOIN resource_collections rc ON r.res_id = rc.resource_id
    WHERE rc.collection_id = ? AND rc.spotlight = 1
    ORDER BY rc.score DESC
    LIMIT 5
""", (slug,)).fetchall()
```

Passed to template as `spotlight_resources=[dict(r) for r in spotlight]`.

### Display Rules

- Max 5 spotlight resources per collection
- Ordered by `resource_collections.score DESC` (existing field)
- If no spotlight resources: section hidden (template guard)
- CSS: simple card grid, consistent with existing design

---

## 4. Files Changed

| File | Change | Lines |
|------|--------|-------|
| `migrations/018_spotlight.sql` | New | +3 |
| `collection_curate.py` | New | ~80 |
| `auto_generate.py` | Query + pass spotlight_resources | +10 |
| `collection.html` | Placeholder already exists — populate with real links | ±0 (placeholder ready) |
| **Total** | | **~93** |

---

## 5. Rollback

```sql
-- Remove spotlight column (SQLite 3.37+)
ALTER TABLE resource_collections DROP COLUMN spotlight;

-- Or just set all to 0
UPDATE resource_collections SET spotlight = 0;
```

No data loss — spotlight is metadata, not content.

---

## 6. Risk Analysis

| Risk | Mitigation |
|------|-----------|
| Spotlight on resource not in collection | CLI checks `resource_collections` row exists before UPDATE |
| Spotlight count per collection too high | `LIMIT 5` in query. No hard cap enforced, but template only shows 5 |
| Editor forgets to run `auto_generate.py` after spotlighting | CLI prints reminder: `💡 python3 auto_generate.py` |
| Migration 018 conflicts with existing `resource_collections` schema | Additive. `spotlight INTEGER DEFAULT 0` — all existing rows get default |

---

确认后编码。
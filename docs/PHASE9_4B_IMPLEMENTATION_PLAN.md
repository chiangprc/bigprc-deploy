# Phase 9.4B — Implementation Plan

> **Status**: Ready to code  
> **Depends on**: v0.9.4a-stable  

---

## A. Migration File Design

### `migrations/016_editorial_status.sql`

```sql
-- Phase 9.4B: Editorial Workflow status columns
-- Additive only. Idempotent. Safe defaults.

ALTER TABLE collection_content ADD COLUMN editorial_status  TEXT DEFAULT 'draft';
ALTER TABLE collection_content ADD COLUMN reviewed_at       TIMESTAMP;
ALTER TABLE collection_content ADD COLUMN approved_at       TIMESTAMP;
```

| Column | Default | Purpose |
|--------|---------|---------|
| `editorial_status` | `draft` | Current state in the workflow |
| `reviewed_at` | NULL | Timestamp of last `--review` |
| `approved_at` | NULL | Timestamp of last `--approve` |

**Idempotent**: `migration.py` skips already-applied migrations. Running `up` twice is safe.

**Rollback**: `ALTER TABLE collection_content DROP COLUMN editorial_status` (SQLite 3.37+ on VPS supports this).

### `migrations/015_audit_log.sql` (must exist before 016)

```sql
CREATE TABLE IF NOT EXISTS collection_audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id   TEXT NOT NULL,
    action          TEXT NOT NULL,
    old_status      TEXT,
    new_status      TEXT,
    operator        TEXT DEFAULT 'editor',
    metadata        TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**This table does not exist on VPS yet.** Migration 015 was designed but never deployed. Must be deployed BEFORE 016.

---

## B. `editorial_review.py` CLI Design

### Commands

```bash
# Status check
python3 editorial_review.py --status                  # all 16 collections
python3 editorial_review.py --status bbc-nature       # single

# Transitions
python3 editorial_review.py --review bbc-nature       # draft → reviewed
python3 editorial_review.py --approve bbc-nature      # reviewed → approved
python3 editorial_review.py --reject bbc-nature       # any → rejected

# Rollback
python3 editorial_review.py --rollback bbc-nature     # restore previous status

# History
python3 editorial_review.py --history bbc-nature      # show audit log for collection
```

### Transition Rules (enforced in Python)

```
Current State     Command          New State      Allowed?
─────────────────────────────────────────────────────
draft             --review         reviewed       ✅
reviewed          --approve        approved       ✅
any               --reject         rejected       ✅
rejected          --review         reviewed       ✅ (re-entry)
any               --rollback       (previous)     ✅
draft             --approve        —              ❌ (skip review step)
approved          --review         —              ❌ (must reject first)
```

### Output Format

```
$ python3 editorial_review.py --review bbc-nature

  BBC 自然纪录片: draft → reviewed
  ✅ Logged to audit

$ python3 editorial_review.py --approve bbc-nature

  ❌ Current status is 'draft', not 'reviewed'.
     Use --review first.
```

### Write guarantees

- Single `UPDATE collection_content SET editorial_status=? WHERE collection_id=?`
- Single `INSERT INTO collection_audit_log (...)`
- Both in one transaction (`try/commit/except/rollback`)
- `--dry-run` mode: prints what would happen, no writes

---

## C. State Machine

```
        ┌─────────┐
        │  draft   │  ← AI writes content (collection_editor_ai.py)
        └────┬─────┘
             │ --review
             ▼
        ┌──────────┐
        │ reviewed  │
        └────┬──────┘
             │ --approve          --reject
             ▼                    ▼
        ┌──────────┐         ┌──────────┐
        │ approved  │         │ rejected  │──→ --review → reviewed
        └──────────┘         └──────────┘

  frontend: collection.html
  already shows content when
  editor_note IS NOT NULL.
  Status is editorial metadata.
```

**Note**: `approved` → `published` is not a distinct state transition. Content is "published" the moment it exists in `collection_content` and `auto_generate.py` renders the static HTML. `editorial_status = 'approved'` means "editor confirms quality." Frontend display uses `{% if editor_note %}` — content presence is the natural show/hide toggle. Status is editorial metadata, not a display gate.

---

## D. Audit Log Write Scheme

```python
def log_audit(cursor, collection_id, action, old_status, new_status, metadata=None):
    cursor.execute("""
        INSERT INTO collection_audit_log
        (collection_id, action, old_status, new_status, operator, metadata)
        VALUES (?, ?, ?, ?, 'editor', ?)
    """, (collection_id, action, old_status, new_status, json.dumps(metadata or {})))
```

Every state change calls this. `--rollback` reads the most recent entry:

```python
def get_previous_status(cursor, collection_id):
    row = cursor.execute("""
        SELECT old_status FROM collection_audit_log
        WHERE collection_id = ? AND action != 'rollback'
        ORDER BY id DESC LIMIT 1
    """, (collection_id,)).fetchone()
    return row[0] if row else 'draft'
```

---

## E. Rollback Scheme

```
$ python3 editorial_review.py --rollback bbc-nature

  Reading audit log...
  Last non-rollback action: review (draft → reviewed)
  Rolling back to: draft
  ✅ BBC 自然纪录片: reviewed → draft
```

**Only restores status.** Does NOT restore editorial content text. Content versioning is Phase 10+.

---

## F. Risk Analysis

| Risk | Mitigation |
|------|-----------|
| Migration 015 not deployed → 016 fails on audit_log INSERT | Run `python3 migration.py up` — deploys both 015 and 016 in sequence |
| editorial_review.py writes to wrong column | Single UPDATE. Only touches `editorial_status, reviewed_at, approved_at` |
| Concurrent CLI runs conflict | SQLite WAL mode handles this. But no two editors on VPS simultaneously. Risk = negligible |
| Rollback to a state that no longer exists in status enum | All states are valid. `draft` is the ultimate fallback |
| editorial.json consumers break on new fields | Additive only. Old JS ignores new keys. |

---

## G. File Modification List

| File | Action | Lines | Purpose |
|------|--------|-------|---------|
| `migrations/015_audit_log.sql` | New (deploy existing design) | +15 | Audit log table |
| `migrations/016_editorial_status.sql` | New | +5 | 3 ALTER TABLE columns |
| `editorial_review.py` | New | ~130 | CLI for status transitions + rollback + history |
| `collection_dashboard_export.py` | Modify (+5) | +5 | Add editorial_status, reviewed_at, approved_at to editorial.json |
| `collection_editor_ai.py` | Modify (+1) | +1 | Set `editorial_status = 'draft'` on `--editorial` write |
| `editorial-detail.html` | Modify (+10) | +10 | Show status badge + CLI command hints |
| `editorial.html` | Modify (+3) | +3 | Activate 🔵 reviewed column |
| **Total** | | **~169** | |

---

确认后进入编码。优先执行 migration 015+016，再创建 editorial_review.py。
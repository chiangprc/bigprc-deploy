# Phase 9.4B — Architecture Review Report

> **Status**: Pre-implementation review  
> **Refers to**: `PHASE9_4B_DESIGN.md`  

---

## 1. State Machine

### Recommend: 4 active states + 1 terminal

```
draft ──→ reviewed ──→ approved
  │          │            │
  │          │            ├──→ archived (terminal)
  │          │            │
  └──────────┴──→ rejected (terminal, from any state)
```

| Current | Action | Next | Allowed | Notes |
|---------|--------|------|---------|-------|
| `draft` | `--review` | `reviewed` | ✅ | AI writes draft. Editor marks as reviewed. |
| `reviewed` | `--approve` | `approved` | ✅ | Editor approves for frontend display. |
| `approved` | `--archive` | `archived` | ✅ | Collection retired, content preserved. |
| `draft` | `--reject` | `rejected` | ✅ | Editor rejects AI-generated content entirely. |
| `reviewed` | `--reject` | `rejected` | ✅ | Found quality issues during review. |
| `approved` | `--reject` | `rejected` | ❌ | Design decision: once approved, rejection means archive. Use `--archive`. |
| `rejected` | `--review` | `reviewed` | ✅ | Re-generate content, re-enter review. |
| `archived` | any | — | ❌ | Terminal state. Cannot be un-archived. |
| any | `--rollback` | previous | ✅ | CLI reads `collection_audit_log`, restores prior status. |

### Transition matrix (SQLite CHECK constraint)

```sql
CHECK(editorial_status IN ('draft','reviewed','approved','rejected','archived'))
```

Logic enforcement is in Python (`editorial_review.py`), not in CHECK — allows flexible evolution.

---

## 2. Database Design

### Decision: Store in `collection_content` (not a new table)

Rationale:
- `collection_content` already holds the editorial fields this status governs
- One row per collection. No JOIN needed for dashboard/export queries.
- The Content layer's `editor_status` (draft/pending/approved/rejected) is for SEO approval. The Editorial layer's `editorial_status` is for curatorial approval. Same table, different columns — no ambiguity.

### Migration 016

```sql
ALTER TABLE collection_content ADD COLUMN editorial_status TEXT DEFAULT 'draft';
ALTER TABLE collection_content ADD COLUMN editorial_reviewed_at TIMESTAMP;
ALTER TABLE collection_content ADD COLUMN editorial_approved_at TIMESTAMP;
```

3 new columns. All have defaults (`draft` for status, NULL for timestamps). Existing 16 collections with editor_note content → status remains `draft`. Existing NULL-editor_note collections → status `draft`.

### Migration safety

| Check | Result |
|-------|--------|
| Idempotent | ✅ `ADD COLUMN` with `IF NOT EXISTS`-style error handling in `migration.py` |
| Backward compatible | ✅ New columns at end of table. All SELECT * queries still work. |
| Rollback | Manual: `ALTER TABLE collection_content DROP COLUMN editorial_status` (SQLite 3.35+ supports DROP COLUMN) |
| No data loss | ✅ `draft` default matches current implicit state |

---

## 3. Audit Log Design

### Reuse `collection_audit_log` (designed in Phase 5.3B, migration 015)

```sql
-- Already in migration 015 (not yet created on VPS)
CREATE TABLE IF NOT EXISTS collection_audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id   TEXT NOT NULL,
    action          TEXT NOT NULL,      -- 'review' / 'approve' / 'reject' / 'archive' / 'rollback'
    old_status      TEXT,               -- editorial_status before
    new_status      TEXT,               -- editorial_status after
    operator        TEXT DEFAULT 'editor',
    metadata        TEXT,               -- JSON: {"reason":"..."}
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Rollback capability

`--rollback` reads the most recent audit_log entry for the collection, restores `old_status`. Does NOT restore content — only status. Content versioning is Phase 10+.

### What audit log does NOT do

- Content snapshots (would double storage ~needlessly)
- Diffs (text diff tool exists outside the system)
- Multi-step undo (only 1 step back)

---

## 4. CLI Design

### `editorial_review.py` commands

```bash
# Transition: draft → reviewed
python3 editorial_review.py --review bbc-nature

# Transition: reviewed → approved
python3 editorial_review.py --approve bbc-nature

# Transition: any → rejected
python3 editorial_review.py --reject bbc-nature --reason "editor_note too generic"

# Transition: approved → archived
python3 editorial_review.py --archive bbc-nature

# Rollback to previous status (reads audit log)
python3 editorial_review.py --rollback bbc-nature

# View status history
python3 editorial_review.py --history bbc-nature

# Batch status check
python3 editorial_review.py --status
```

### Safety

- `--approve` requires `editorial_status = 'reviewed'`. Rejects if current is `draft`.
- `--review` requires `editorial_status = 'draft'`. Rejects if already reviewed.
- All transitions log to `collection_audit_log`.
- All commands are idempotent (running `--review` twice on same collection is safe — second call logs but doesn't change status).

---

## 5. Architecture Compatibility

| Frozen Interface | Phase 9.4B Impact |
|-----------------|-------------------|
| `collection_editor_ai.py` | ✅ No change. Sets `editorial_status = 'draft'` on write (1 line addition, backward compatible) |
| `editorial.json` schema | ✅ Additive: +3 fields (editorial_status, reviewed_at, approved_at). No removals. |
| `collection_dashboard_export.py` | ✅ Add 3 fields to `build_editorial_status()` SELECT. |
| Dashboard / collections / editorial pages | ✅ `editorial.html` shows 🔵 reviewed status (reserved column now active). `editorial-detail.html` shows status badge + CLI hints. |
| Frontend (`collection.html` template) | ✅ Already has `{% if editor_note %}` blocks. Status check not needed — content presence is the natural toggle. |
| `auto_generate.py` | ✅ No change. Static generation reads content, not status. |

---

## 6. Risk Analysis

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Migration fails on older SQLite (< 3.35 DROP COLUMN unsupported) | Low | VPS runs Ubuntu 22.04, SQLite 3.37+. DROP COLUMN supported. |
| `editorial_review.py` writes to wrong column | Low | Single-purpose script. Only modifies `editorial_status + *_at` columns. |
| Audit log table doesn't exist (migration 015 not yet run) | High | Must run migration 015 BEFORE 016. Deployment order matters. |
| CLI misuse (e.g. `--approve` before `--review`) | Low | State transition validation in Python. Illegal transitions print error + exit. |
| editorial.json schema change breaks existing pages | Low | Additive only. New fields ignored by old JS. |

## 7. Implementation Plan

| Sub-phase | Deliverable | Lines | Schema |
|-----------|-----------|-------|--------|
| 9.4B.1 | `migrations/016_editorial_status.sql` (3 ALTER TABLE) + `migrations/015_audit_log.sql` (if needed) | +15 | 2 new columns + 1 new table |
| 9.4B.2 | `editorial_review.py` (--review/--approve/--reject/--archive/--rollback/--history/--status) | ~120 | None |
| 9.4B.3 | `collection_dashboard_export.py` (add 3 fields to editorial.json) + `collection_editor_ai.py` (set editorial_status='draft' on write) | +5 | None |
| 9.4B.4 | `editorial-detail.html` (status badge + CLI hints) + `editorial.html` (🔵 column activation) | +15 | None |

**Total: ~155 lines. 1 migration. Zero existing-page breakage.**

---

## 8. Recommendation

**Proceed with Phase 9.4B.1.** Run migration 015 first (audit_log table), then 016 (editorial_status columns). Both are additive and backward-compatible.
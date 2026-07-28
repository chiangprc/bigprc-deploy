# Phase 9.4B — Editorial Review Workflow Design

> **Status**: Design  
> **Depends on**: v0.9.4a-stable (editorial-detail page)  

---

## 1. Problem

Currently, `collection_content` has 4 editorial fields (editor_note, why_collect, audience, highlights) and `editorial.html` shows a 🔵 "已审核" status is reserved but never activated. There is no state machine for editorial content. The `collection_editor_ai.py` pipeline generates draft content but there is no "reviewed → approved → published" flow.

---

## 2. State Machine Design

```
AI generated (--editorial)
        │
        ▼
    [draft]          ← 初始状态。AI 写入后默认为 draft。
        │
        ▼ (editor reviews)
    [reviewed]        ← 编辑在 editorial-detail 页面确认内容无误
        │
        ▼ (editor approves)
    [approved]        ← 编辑正式批准发布
        │
        ▼
    [published]       ← 前端展示 (auto_generate.py 已处理)

生命周期结束?:
        │
        ▼
    [archived]        ← 专题下线/内容过时 (Phase 9.x+)

回退:
    [approved] → [draft]   ← 编辑发现质量问题，打回重新生成
```

## 3. Where to Store Status

**Option A**: New column `editorial_status` on `collection_content` table.

| Pros | Cons |
|------|------|
| Clean separation from collection lifecycle (collections.status) | Requires migration (Phase 9.4B would be the first editorial migration) |

**Option B**: Reuse existing `collection_content.editor_status` column. This column already exists but is only used for Content layer (seo_desc approval).

| Pros | Cons |
|------|------|
| No migration needed | Ambiguous — mixes Content approval with Editorial approval |

**Recommendation**: New column. Editorial lifecycle is distinct from Content lifecycle. Migration 016: `ALTER TABLE collection_content ADD COLUMN editorial_status TEXT DEFAULT 'draft'`. One ALTER TABLE. Backward compatible.

---

## 4. Write Strategy

### Write path

```
editorial-detail.html (browser)
        │  editor clicks "Approve" → sends to...?
        │
        ▼
???

Problem: Static HTML can't write to SQLite.
```

**Solution**: Write stays in CLI. `editorial_review.py` — a dedicated script for status transitions.

```bash
# Mark as reviewed
python3 editorial_review.py --review bbc-nature

# Approve (activate frontend display)
python3 editorial_review.py --approve bbc-nature

# Reject / send back to draft
python3 editorial_review.py --reject bbc-nature --reason "editor_note too marketing-heavy"
```

**CLI only**. No browser write path. This maintains the architectural invariant: "all writes go through CLI." The editorial-detail page shows the current status and a `💡` command hint.

### Data safety

- `editorial_review.py` only modifies `collection_content.editorial_status`. Never touches other columns.
- No auto-approve. Always requires explicit human command.
- Status transitions are logged to `collection_audit_log` (table already exists from Phase 5.3B design — migration 015).

### Rollback mechanism

```bash
# View status history
python3 editorial_review.py --history bbc-nature

# Rollback to previous status
python3 editorial_review.py --rollback bbc-nature
```

Rollback reads `collection_audit_log` for the previous status, restores it. No versioning of content — only status rollback.

---

## 5. UI Integration

### editorial-detail.html changes

Add a **status badge** in the header:

```
BBC 自然纪录片                                    🟢 reviewed
```

Add **command hints** in the footer (replacing static links):

```
── 操作 ──────────────────────────────────────
当前状态: draft
💡 python3 editorial_review.py --review bbc-nature    # Mark as reviewed
💡 python3 editorial_review.py --approve bbc-nature   # Approve for publishing
```

### editorial.html changes

Activate the reserved 🔵 column:

```
状态: ⚪ empty → 🟡 draft → 🔵 reviewed → 🟢 approved
```

Add `editorial_status` to `editorial.json` export.

---

## 6. Data Flow

```
collection_editor_ai.py --editorial
  → writes editor_note/why_collect/audience/highlights
  → sets editorial_status = 'draft'
        │
        ▼
editorial-detail.html (review)
        │
        ▼
editorial_review.py --review bbc-nature
  → sets editorial_status = 'reviewed'
  → logs to collection_audit_log
        │
        ▼
editorial_review.py --approve bbc-nature
  → sets editorial_status = 'approved'
  → collection.html template: {% if editorial_status == 'approved' %} show editorial section
        │
        ▼
auto_generate.py (already handles this — templates check field presence, not status)
```

---

## 7. Implementation Plan

| Phase | Files | Lines | Schema |
|-------|-------|-------|--------|
| 9.4B.1 | `migration 016` (editorial_status column) | +3 SQL | 1 ALTER TABLE |
| 9.4B.2 | `editorial_review.py` (--review/--approve/--reject/--history/--rollback) | ~120 | None |
| 9.4B.3 | `collection_dashboard_export.py` (add editorial_status to editorial.json) | +3 | None |
| 9.4B.4 | `editorial.html` + `editorial-detail.html` (show status + command hints) | +20 | None |

---

## 8. Freeze Boundaries

| Constraint | Compliance |
|-----------|-----------|
| No auto-approve | CLI requires explicit command |
| No browser write | All writes via CLI |
| Audit trail | `collection_audit_log` table |
| Rollback support | `--rollback` reads history |
| Backward compatible | Existing collections default to 'draft' |

---

确认后进入 Phase 9.4B.1 编码。
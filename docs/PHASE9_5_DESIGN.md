# Phase 9.5 — Editorial Publish Gate Design

> **Status**: Design  
> **Depends on**: v0.9.4b-stable (Editorial Workflow)  

---

## A. Goal

Add a publish gate between "editor approved" and "user sees it on the frontend."

## B. Current Problem

Today: content written to `collection_content` → `auto_generate.py` runs → `/collection/{slug}.html` shows all content. There is no "approved but not yet shown" state. The editor's approval has no effect on frontend display.

Desired: editor approves → content is gated → explicit publish action → frontend shows content.

## C. State Machine

```
draft ──→ reviewed ──→ approved ──→ published
  │         │            │              │
  │         │            │              ├──→ unpublished (revert)
  │         │            │              │
  └─────────┴────────────┴──→ rejected
```

| Current | Command | Next | Allowed |
|---------|---------|------|---------|
| `draft` | `--review` | `reviewed` | ✅ |
| `reviewed` | `--approve` | `approved` | ✅ |
| `approved` | `--publish` | `published` | ✅ |
| `published` | `--unpublish` | `approved` | ✅ |
| any | `--reject` | `rejected` | ✅ |
| any | `--rollback` | (previous) | ✅ |

### Key Design Decision: `approved` ≠ `published`

| State | Meaning |
|-------|---------|
| `approved` | Editor says: "content quality is good." Internal signal. |
| `published` | System says: "this content is visible on the frontend." External signal. |

Why separate them:
- Editor can approve 5 collections in a batch, then publish them together
- Unpublish (hide content) without losing approval status
- Rollback from published → approved (not all the way to draft)

## D. Data Design

### Recommendation: `editorial_status` column only. No new table. No new column.

The existing `editorial_status` column (migration 016) already stores states as TEXT. Simply add `'published'` and `'unpublished'` to the valid values. No schema change needed.

```sql
-- editorial_status already supports arbitrary TEXT values.
-- Phase 9.5 just adds two new values: 'published', 'unpublished'
-- No ALTER TABLE required.
```

### Frontend display gate

Current template:
```jinja
{% if editor_note %}
<div class="editorial">{{ editor_note }}</div>
{% endif %}
```

Proposed change:
```jinja
{% if editor_note and editorial_status == 'published' %}
<div class="editorial">{{ editor_note }}</div>
{% endif %}
```

This means: content exists AND publish gate is open → show. Content exists but not published → hidden.

### `editorial.json` impact

Add `editorial_status` to the export (already done in Phase 9.4B). No additional changes needed.

## E. CLI Design

### Extend `editorial_review.py` (not a new script)

```bash
# Publish
python3 editorial_review.py --publish bbc-nature
# approved → published

# Unpublish (hide from frontend)
python3 editorial_review.py --unpublish bbc-nature
# published → approved

# Status
python3 editorial_review.py --status bbc-nature
# Shows: 🟢 published  bbc-nature  BBC 自然纪录片
```

### Why extend rather than create new script

- Same table (`collection_content.editorial_status`)
- Same audit log (`collection_audit_log`)
- Same transition validation pattern
- Adding `--publish`/`--unpublish` to existing script = +20 lines. New script = +80 lines (duplicated DB connection, audit logging, error handling).

## F. Frontend Impact

| File | Change | Lines |
|------|--------|-------|
| `collection.html` (Jinja2 template) | `{% if editor_note %}` → `{% if editor_note and editorial_status == 'published' %}` | ±1 |
| `auto_generate.py` | `build_collection_pages()` already reads `collection_content` via LEFT JOIN. Add `editorial_status` to SELECT (if not already), pass to template. | +2 |
| `editorial-detail.html` | Add 'published' to status icon map + CLI hints | +3 |

### Static generation trigger

No automatic trigger. Editor runs `auto_generate.py` after publishing. This is consistent with the existing workflow: all content changes require explicit regeneration.

```bash
# Editor workflow
python3 editorial_review.py --approve bbc-nature
python3 editorial_review.py --publish bbc-nature
python3 auto_generate.py                    # regenerate static HTML
```

## G. Risk Analysis

| Risk | Mitigation |
|------|-----------|
| Existing 16 collections: content written but editorial_status='draft', frontend shows content anyway | On migration, set all existing collections with content to `editorial_status='published'` (one-time SQL) |
| `auto_generate.py` doesn't pass `editorial_status` to template | Add 1 field to SELECT + 1 field to render() |
| Editor forgets to run `auto_generate.py` after publish | CLI prints reminder: `💡 python3 auto_generate.py` |
| Unpublish hides content that users bookmarked | Content is hidden, not deleted. Re-publish restores. |

## H. File Modification List

| File | Change | Lines |
|------|--------|-------|
| `editorial_review.py` | + `--publish` / `--unpublish` commands + transitions | +20 |
| `collection.html` (template) | Add `editorial_status == 'published'` gate | ±1 |
| `auto_generate.py` | Pass `editorial_status` to collection template render | +2 |
| `editorial-detail.html` | Add 'published' icon + CLI hint | +3 |
| **Total** | | **~26** |

**Zero migrations. Zero new tables. Zero new scripts.**

---

## Recommendation

Phase 9.5 is a ~26-line change. The publish gate adds editorial control over frontend visibility without new infrastructure. All changes are additive to existing files.

确认后进入编码。
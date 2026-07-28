# Phase 9.4A — Editorial Detail Page Release Notes

> **Tag**: `v0.9.4a-stable`  
> **Date**: 2026-07-29  
> **Status**: Frozen  

---

## Delivered

1. **`collection_dashboard_export.py`**: `build_editorial_status()` now exports full text for all 4 editorial fields + `resource_count`. `editorial.json` is the single data source for editorial pages.

2. **`/admin/editorial-detail.html?id=`**: Read-only editorial review page. Shows header (title, id, resource count, completion status) + 4 editorial cards with 🟢/🔴 status dots + full text. AI metadata timestamp. Links to frontend and editorial dashboard.

3. **`/admin/editorial.html`**: Collection titles now link to `editorial-detail.html` instead of `collection-detail.html`.

## Architecture Invariants Preserved

- Read-only (fetch JSON, no writes)
- Zero schema changes
- Zero pipeline changes (`collection_editor_ai.py` untouched)
- `editorial.json` schema freeze (additive only — 4 text fields + resource_count added, no removals)
- Static HTML + JSON fetch
- CLI → JSON → Static HTML

## Files Changed

| File | Lines |
|------|-------|
| `collection_dashboard_export.py` | +7 |
| `editorial-detail.html` | +93 (new) |
| `editorial.html` | ±1 |
| **Total** | **+101** |

# Phase 9.3 — Editorial Dashboard Release Notes

> **Tag**: `v0.9.3-stable`  
> **Date**: 2026-07-29  
> **Status**: Frozen  

---

## 1. Release Summary

Phase 9.3 built the Editorial Dashboard — the first dedicated editorial workspace page. It provides editors with a read-only overview of editorial content completeness across all 16 collections.

### 9.3A — Editorial Export + Collections Enhancement

- `collection_dashboard_export.py`: new `build_editorial_status()` function reads `collection_content` fields and computes 4-level status
- Exports `editorial.json` alongside existing dashboard/collections/details JSON
- `collections.html`: new Editorial column with status indicator (⚪🟡🟢)

### 9.3B — Editorial Dashboard

- New page: `/admin/editorial.html`
- 4 summary cards: total collections, complete, incomplete, completion rate
- Data freshness indicator
- 16-collection status table: per-field red/green dots + completion progress bar
- Collection titles link to collection-detail page
- Quick links to collections, review, dashboard

---

## 2. Data Flow

```
collection_content table
  (editor_note, why_collect, audience, highlights)
        │
        ▼
collection_dashboard_export.py
  build_editorial_status()
        │
        ▼
/var/www/site/web/admin/data/editorial.json
        │
        ▼
/admin/editorial.html  ←  fetch() + render
/admin/collections.html ←  editorial status column
```

---

## 3. Architecture State

| Layer | Version | Status |
|-------|---------|--------|
| Rule Engine | `v0.8-stable` | Frozen |
| Content (SEO/FAQ) | Phase 6 Stable | Stable |
| Editorial Pipeline | `v0.9.2-stable` | Frozen |
| Editorial Dashboard | `v0.9.3-stable` | Frozen |
| Collections (enhanced) | `v0.9.3a-stable` | Frozen |
| Admin Dashboard | Phase 7 Stable | Stable |

---

## 4. Frozen Interfaces

| Interface | Frozen Since | Change Requires |
|-----------|-------------|----------------|
| `build_editorial_status()` | v0.9.3a | RFC |
| `editorial.json` schema | v0.9.3a | RFC (additive only) |
| `editorial.html` page structure | v0.9.3b | RFC |
| `collections.html` Editorial column | v0.9.3a | RFC |
| `collection_editor_ai.py` pipeline | v0.9.2 | RFC |
| `collection_content` table | Phase 6 | Migration |

---

## 5. Known Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|-----------|
| All editorial content read-only in dashboard | Editor must use CLI to generate/write | Phase 9.4 will add editorial editor page |
| No per-field approval workflow | All 4 fields written or none | Phase 9.4 |
| No batch editorial audit | Must open each collection individually | Phase 9.4 |
| 🔵 已审核 status is reserved but unused | UI ready, no data source | Phase 9.4 will enable |
| editorial.json must be manually regenerated | Stale data if collections change | `python3 collection_dashboard_export.py` |

---

## 6. Files Changed (Phase 9.3)

| File | Change | Lines |
|------|--------|-------|
| `collection_dashboard_export.py` | +50: `build_editorial_status()` | +50 |
| `collections.html` | +13: Editorial status column | +13 |
| `editorial.html` | New: 85 lines | +85 |
| `dashboard.html` | +1: editorial quick link | +1 |
| **Total** | | **+149** |

---

## 7. Phase 9.4 Candidates

| Priority | Feature | Goal |
|----------|---------|------|
| 1 | Editorial Detail Page (`/admin/editorial-detail.html?id=`) | Read and review all 4 editorial fields for a single collection. Pre-filled text areas (read-only). |
| 2 | Editorial Write CLI (`editorial_save.py`) | Write approved editorial content to collection_content via CLI |
| 3 | 🔵 已审核 status activation | Toggle reserved status when editor approves editorial content |
| 4 | Frontend Integration | Verify editorial content renders on `/collection/{slug}.html` |

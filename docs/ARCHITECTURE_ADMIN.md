# BigPRC Admin Backend — Architecture Document

> **Version**: Phase 6 Stable
> **Last Updated**: 2026-07-28

---

## 1. Page Responsibilities

### `/admin/dashboard.html` — Editorial Home

**Solves**: "What should I do today?"

**Audience**: Editor starting their shift.

**Input JSON**: `dashboard.json`

| Section | Content | Action |
|---------|---------|--------|
| Summary cards | Total collections, CORE count, pending reviews, expand rules | Click cards → target page |
| Health status | stable/warning/unstable counts | Click badge → collections filtered |
| Recent findings | Top 10 NEW_COLLECTION / EXPAND_RULE items from Discovery | Read-only |
| Quick links | collections, review, frontend index | Navigation |

### `/admin/collections.html` — Collection List

**Solves**: "Which collections need attention?"

**Audience**: Editor browsing/managing all collections.

**Input JSON**: `collections.json`

| Feature | Description |
|---------|-------------|
| Search | Filter by title or ID |
| Sort | Click column headers (resource count, quality, health) |
| Filter | Dropdown by quality tier or health status |
| Detail link | Each row → `collection-detail.html?id=` |

### `/admin/collection-detail.html` — Collection Deep Dive

**Solves**: "What's really going on with this specific collection?"

**Audience**: Editor analyzing a single collection.

**Input JSON**: `collection-details.json`

| Section | Purpose |
|---------|---------|
| Header | Title, ID, quality/health badges, featured/auto tags |
| Metric cards | Resource count, exclusive, shared, exclusive % |
| Rule Summary | Natural-language tag/category display (no JSON) |
| Rule Validation | Match count vs DB, delta %, health, tag/category pools |
| Raw JSON | Collapsible `<details>` (debug only) |
| Top Tags | Frequency-ranked tags in collection resources |
| Shared Collections | Overlapping collections with shared % |
| Samples | First 50 resources with ID/title/category |
| Placeholders | Editor Notes, Recent Changes, AI Suggestion (Phase 6 reserved) |
| Navigation | ← Previous / Frontend page / Next → |

### `/admin/collection-review.html` — Discovery Review

**Solves**: "Which NEW_COLLECTION / EXPAND_RULE findings should I act on?"

**Audience**: Editor reviewing Discovery output.

**Input JSON**: `review-data.json`

| Feature | Description |
|---------|-------------|
| Filter | ALL / KEEP / EXPAND_RULE / NEW_COLLECTION / MERGE_REVIEW |
| Sort | By match count, uncovered count, or coverage % |
| Expandable resources | Per-group sample list with covered/uncovered indicators |
| Representative tags | Context tags for each group |

---

## 2. Data Flow

```
SQLite (database.db)
    │
    ├── collection_dashboard_export.py
    │   ├── build_dashboard()          → dashboard.json
    │   ├── build_collections()        → collections.json
    │   └── build_collection_details()  → collection-details.json
    │
    └── collection_review_export.py
        └── pipeline(discovery → gap)  → review-data.json

                    ↓
              /var/www/site/web/admin/data/
                    ↓
                Nginx (gzip, cache 3600s)
                    ↓
            Static HTML + fetch(JSON)
                    ↓
                  Editor (browser)
```

**Export is explicit. No cron, no auto-refresh. Editor runs export when new data is available.**

---

## 3. JSON Schema

### `dashboard.json`

```
{
  "generated_at": "ISO timestamp",
  "summary": {
    "total_collections": int,
    "featured": int,
    "auto_generated": int,
    "core": int,           // >= 100 resources
    "solid": int,           // >= 20
    "niche": int            // >= 5
  },
  "health": {
    "total_issues": int,
    "high": int,
    "medium": int,
    "stable": int
  },
  "review_pending": {
    "new_collection": int,
    "expand_rule": int,
    "keep": int
  },
  "recent_findings": [
    {
      "candidate_tags": [string],
      "match_count": int,
      "action": "NEW_COLLECTION" | "EXPAND_RULE",
      "action_label": string,
      "best_match": { "id": string, "title": string, "covered_count": int } | null
    }
  ]
}
```

### `collections.json`

```
[{
  "id": string,
  "title": string,
  "resource_count": int,
  "quality": "CORE" | "SOLID" | "NICHE" | "THIN" | "EMPTY",
  "health": "stable" | "warning" | "unstable" | "empty" | "broken",
  "featured": bool,
  "auto_generated": bool,
  "rule_json": string       // JSON-encoded rule, for inline preview
}]
```

### `collection-details.json`

```
[{
  "id": string,
  "title": string,
  "quality": string,       // CORE|SOLID|NICHE|THIN|EMPTY
  "health": string,        // stable|warning|unstable|empty|broken
  "featured": bool,
  "auto_generated": bool,
  "resource_count": int,
  "exclusive_count": int,
  "shared_count": int,
  "exclusive_pct": int,
  "coverage_pct": float,
  "rule": {                // parsed dict, NOT JSON string
    "tags": [string],
    "tags_or": [string],
    "cats": [string],
    "exclude_tags": [string] | null,
    "version": int
  },
  "engine_match": int,
  "engine_delta_pct": float,
  "engine_summary": {
    "matched": int,
    "tags": [{"name": string, "count": int}],
    "tags_or": [{"name": string, "count": int}],
    "categories": [{"name": string, "count": int}]
  },
  "top_tags": [{"name": string, "count": int}],
  "shared_collections": [
    {"id": string, "title": string, "shared": int, "shared_pct": float}
  ],
  "samples": [{"id": string, "title": string, "category": string}],  // max 50
  "editor_notes": null | string,
  "recent_changes": null | string,
  "ai_suggestion": null | string
}]
```

### `review-data.json`

Generated by `collection_review_export.py` → pipe(discovery → gap).

```
{
  "generated_at": "ISO timestamp",
  "total_groups": int,
  "summary": {
    "KEEP": int, "EXPAND_RULE": int, "NEW_COLLECTION": int, "MERGE_REVIEW": int
  },
  "groups": [
    {
      "candidate_tags": [string],
      "match_count": int,
      "covered_count": int,
      "uncovered_count": int,
      "coverage_pct": int,
      "action": "KEEP" | "EXPAND_RULE" | "NEW_COLLECTION" | "MERGE_REVIEW",
      "action_label": string,
      "reason": string,
      "best_match": {"id": string, "title": string, "covered_count": int} | null,
      "top_matches": [...],
      "representative_tags": [string],
      "title_keywords": [string],
      "resource_samples": [
        {
          "id": string,
          "title": string,
          "covered": bool,
          "collections": [{"id": string, "title": string}]
        }
      ]
    }
  ]
}
```

---

## 4. Page Relationships

```
                 ┌──────────────┐
                 │  Dashboard   │
                 └──┬───┬───┬──┘
                    │   │   │
        ┌───────────┘   │   └──────────┐
        ▼               ▼              ▼
┌──────────────┐ ┌───────────┐ ┌──────────────┐
│ Collections  │ │  Review   │ │ Frontend     │
│              │ │           │ │ Index        │
└──────┬───────┘ └───────────┘ └──────────────┘
       │
       ▼
┌──────────────┐
│  Detail      │
│  ← prev      │
│  next →      │
└──────────────┘
```

---

## 5. Export Pipeline

### Scripts

| Script | Generates | When to run |
|--------|-----------|-------------|
| `collection_dashboard_export.py` | dashboard.json, collections.json, collection-details.json | After any collection change (create/update/delete) |
| `collection_review_export.py` | review-data.json | After running discovery + gap pipeline |

### Deploy Flow

```bash
# 1. Export data
cd /root/scripts
python3 collection_dashboard_export.py
python3 collection_review_export.py

# 2. Data is written to /var/www/site/web/admin/data/

# 3. Browsers fetch static JSON via Nginx (no server restart needed)

# 4. If HTML templates changed:
cd /root/bigprc-deploy && bash deploy.sh
```

**When to re-export**: After any database change that affects collections or resource_collections.

**When NOT to re-export**: After HTML/CSS/JS changes only (just deploy.sh).

---

## 6. Architecture Invariants

All future development MUST follow these rules:

### Data Architecture
1. **CLI → JSON → Static HTML** — This is the only allowed data path
2. **Browser never connects to SQLite** — No direct DB access from frontend
3. **All pages are read-only** — No POST/PUT/DELETE endpoints
4. **No Node, PHP, FastAPI, or any server runtime** — Nginx serves static files only

### JSON Contract
5. **JSON fields are append-only** — Adding new fields is OK; removing or renaming existing fields breaks pages
6. **New pages reuse existing JSON** — Don't create a new export just for one page unless absolutely necessary
7. **Export does the work, browser does the display** — All computation (quality tiers, health checks, engine matching) happens in Python during export

### CLI
8. **Writes go through CLI** — Creating/updating collections, rules, tags is done via Python scripts run on VPS
9. **No auto-refresh, no cron for admin data** — Editor explicitly runs export when they want fresh data

### Code
10. **No shared JS modules across admin pages (for now)** — Each page is self-contained. Shared libs can be introduced when there are 5+ pages sharing the same logic.

---

## 7. File Inventory

```
root/custom-pages/admin/
├── dashboard.html              Phase 6.0  Editorial home
├── collections.html            Phase 6.0  Collection list (search/sort/filter)
├── collection-detail.html      Phase 6.1  Collection deep dive
├── collection-review.html      Phase 5.3E Discovery review panel
└── data/                       Generated JSON (not in git)
    ├── dashboard.json          collection_dashboard_export.py
    ├── collections.json        collection_dashboard_export.py
    ├── collection-details.json collection_dashboard_export.py
    └── review-data.json        collection_review_export.py

root/scripts/
├── collection_dashboard_export.py   Phase 6.0  Dashboard + Collections + Details export
├── collection_review_export.py      Phase 5.3E Review data export pipeline
├── collection_discovery.py          Phase 5.3B Tag co-occurrence discovery
├── collection_gap.py                Phase 5.3D Coverage gap analysis
├── collection_rule_assist.py        Phase 5.3F Rule creation CLI
├── rule_engine.py                   Phase 5.3A Python→SQL rule parser
├── collection_quality_report.py     Phase 5.4  Quality analysis
├── collection_health.py             Phase 5.4  Health checks
└── collection_strategy_report.py    Phase 5.5  Strategy analysis
```

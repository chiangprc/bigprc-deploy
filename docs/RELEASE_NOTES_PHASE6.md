# BigPRC Phase 6 Release Notes

> **Tag**: `v0.6-admin-stable`
> **Date**: 2026-07-28
> **Status**: Stable

---

## New Pages

| Page | Phase | Purpose |
|------|-------|---------|
| `/admin/dashboard.html` | 6.0 | Editorial workspace home: summary stats, health, recent findings |
| `/admin/collections.html` | 6.0 | All collections with search, sort, filter, quality/health badges |
| `/admin/collection-detail.html` | 6.1 | Single collection deep dive: rule breakdown, match validation, tags, samples |
| `/admin/collection-review.html` | 5.3E | Discovery review panel: filter/sort/expand findings from gap analyzer |

## New Scripts

| Script | Purpose |
|--------|---------|
| `collection_dashboard_export.py` | Exports dashboard.json, collections.json, collection-details.json |
| `collection_review_export.py` | Pipes discovery → gap → review-data.json |
| `collection_discovery.py` | Tag co-occurrence pattern scanner |
| `collection_gap.py` | Coverage gap analyzer |
| `collection_rule_assist.py` | CLI rule creation with YES-confirm safety |
| `rule_engine.py` | Python→SQL rule parser and match engine |
| `collection_quality_report.py` | Per-collection quality analysis |
| `collection_health.py` | Automated health checks (empty/thin/dead/overlap) |
| `collection_strategy_report.py` | Homepage ranking + relationships + stability |

## Completed Features

- **Editorial Dashboard**: Summary cards, health status, recent findings, quick links
- **Collection Management**: Search, sort, filter by quality/health, detail links
- **Collection Deep Dive**: Natural-language rule display, match validation, engine breakdown, tag pools, shared collections with overlap %, resource samples, prev/next navigation
- **Rule Engine**: Python-based rule parser supporting tags (AND), tags_or (OR), cats filter, exclude_tags. Match results validated against database counts
- **Discovery Pipeline**: Tag co-occurrence → gap analysis → review dashboard → rule creation CLI
- **Quality & Health Reports**: CORE/SOLID/NICHE/THIN/EMPTY tiers, empty/thin/dead-rule/overlap checks
- **Strategy Report**: Homepage ranking, parent-child candidates, merge suggestions, rule stability tiers

## Fixed Issues

- `qColor`/`hColor` Safari compatibility (function expressions)
- `cursor not defined` in build_collection_pages (moved to fetch_collections_from_db)
- `tag_list` undefined after plan-mode refactor
- SQL binding mismatch in plan mode
- HAVING COUNT(*) >= min_resources filtering bug
- Duplicate resource_collections after fragment merge
- UNIQUE constraint on resource_collections during merge
- `.env` fallback path for VPS symlink resolution
- `Disallow: /go/` conflict with sitemap
- AI bot crawler blocking in robots.txt
- Summary audit threshold (50→80 chars)
- Tagline English/Chinese length mismatch
- "顶级"/"第一" false rejections

## Current Limitations

| Limitation | Reason | Planned |
|-----------|--------|---------|
| All writes must be done via CLI (SSH) | By design: static architecture | Phase 7 may add localhost helper |
| No authentication on admin pages | Data is read-only and public | Phase 7 adds IP restriction |
| Data must be manually exported (`python3 collection_dashboard_export.py`) | No cron for admin data | Phase 7 may add auto-export on collection change |
| Editor Notes / Recent Changes / AI Suggestion are placeholder sections | No persistence layer | Phase 7 |
| No bulk operations (batch mark-as-reviewed, batch merge) | CLI is single-operation | Phase 7 |
| No notification when new Discovery results are available | No polling/websocket | Phase 7 |

## Architecture Invariants

These rules were established in Phase 6 and carry forward:

1. Admin pages are static HTML + JSON fetched via `fetch()`
2. Browser never connects to SQLite directly
3. No server runtime (Node/PHP/FastAPI/Flask)
4. JSON fields are append-only (add OK, remove/rename forbidden)
5. All computation happens in Python export scripts
6. Writes go through CLI with explicit confirmation
7. Export is explicit, not automatic

## Next Steps (Phase 7 Candidates)

- Collection merge/split CLI
- Rule suggestion based on gap analysis
- Editor Notes persistence
- IP-restricted admin access
- Auto-export on pantools_sync_v2 completion
- Shared JS library for admin pages

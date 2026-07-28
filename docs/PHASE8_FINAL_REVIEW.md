# Phase 8 — Rule Engine Final Architecture Review

> **Status**: Frozen  
> **Tag**: `v0.8-stable`  
> **Date**: 2026-07-28  

---

## 1. Phase 8 Deliverables

### Core Engine

| Component | File | Description |
|-----------|------|-------------|
| Rule Parser | `rule_engine.py` | Python→SQL rule converter. AND/OR/CATS/EXCLUDE support |
| Match Engine | `rule_engine.py` | `match_collection()` — deterministic SQL matching |
| Rule Verification | `rule_engine.py` | `match_all()`, `diff_collection()` — dual-write verification |
| Rule Creation | `collection_rule_assist.py` | `--preview` / `--propose` / `--apply` with YES confirm |
| Rule Simulation | `collection_rule_assist.py` | `--simulate` — read-only impact preview |

### Analysis & Monitoring

| Component | File | Description |
|-----------|------|-------------|
| Gap Analysis | `collection_gap.py` | Engine match vs DB count, coverage classification |
| Gap Evidence | `collection_dashboard_export.py` | Per-tag frequency on missing/extra resources + impact preview |
| Health Checks | `collection_health.py` | empty/thin/dead_rule/overlap detection |
| Quality Tiers | `collection_quality_report.py` | CORE/SOLID/NICHE/THIN/EMPTY classification |
| Strategy Report | `collection_strategy_report.py` | Homepage ranking, parent-child, merge candidates, stability |

### UI (Admin)

| Page | Rule-Related Sections |
|------|----------------------|
| `collection-detail.html` | Rule Summary, Rule Gap Analysis, Impact Preview, Action Panel, Rule JSON, High-Frequency Tags, Shared Collections, Resource Samples (10) |
| `collections.html` | Quality tier + health status per collection |
| `dashboard.html` | Health summary: stable/warning/unstable counts |

---

## 2. Architecture Decisions

### What Phase 8 Deliberately Excluded

| Capability | Reason for Exclusion |
|-----------|---------------------|
| Rule History / Versioning | No current need. 16 collections. Would incur DB schema + maintenance cost. |
| `min_tags` threshold | Current AND/OR logic sufficient for 16 collections. |
| `platform` / `file_format` filter | Not needed. Category filter already achieves most of this. |
| AI-powered rule tuning | Violates editor-in-the-loop principle. Rules are deterministic. |
| Browser-based Playground | Violates CLI→JSON→Static HTML architecture. Would need backend. |
| Editorial Status Bar | Belongs in Phase 9 Editorial Workflow, not Rule Debug Tool. |
| Shared Collection Relations (高度重叠/互补) | Overlap % is sufficient at current scale. |

### What Phase 8 Built

```
Rule Engine Lifecycle:

  Discovery (collection_discovery.py)
    → tag co-occurrence patterns
  
  Gap Analysis (collection_gap.py)
    → KEEP / EXPAND_RULE / NEW_COLLECTION / MERGE_REVIEW
  
  Review Dashboard (/admin/collection-review.html)
    → Editor browses findings, gets CLI bridge commands
  
  Rule Assist CLI
    --preview <group_id>  → see rule draft
    --propose <group_id>  → create draft JSON
    --simulate <id> ...    → preview impact before applying
    --apply <slug>         → write to DB (YES confirm)
  
  Monitoring
    collection-detail.html → Rule Summary + Gap Evidence + Action Panel
    collections.html       → quality + health scan
    collection_health.py   → automated issue detection
```

---

## 3. Data Flow (Final State)

```
Rule Creation
  collection_discovery.py --json
  | collection_gap.py --json
  → /admin/data/review-data.json
  → /admin/collection-review.html
  → editor decision
  → collection_rule_assist.py --propose / --simulate / --apply
  → collections.rule_json

Rule Monitoring
  collection_dashboard_export.py
  → /admin/data/collection-details.json
  → /admin/collection-detail.html
  → Rule Summary / Gap Analysis / Action Panel

Health & Quality
  collection_health.py
  collection_quality_report.py
  collection_strategy_report.py
  → included in dashboard export
  → /admin/dashboard.html + /admin/collections.html
```

---

## 4. Rule Engine Contract

### `rule_json` Schema (v1)

```json
{
  "tags": ["string"],           // AND logic — resource must have ALL
  "tags_or": ["string"],        // OR logic — resource must have at least ONE
  "cats": ["string"],           // Category filter — resource category must match
  "exclude_tags": ["string"],   // Exclusion — resource must NOT have these
  "min_resources": int,          // Minimum resources to create collection
  "version": 1                   // Schema version
}
```

### `parse_rule()` Contract

- Input: `rule_json` dict
- Output: `(WHERE_clause: str, params: list, warnings: list)`
- All tags/cats validated against actual database content
- Unknown fields silently ignored (forward-compatible)

### `match_collection()` Contract

- Input: `cursor`, `rule_json`, optional `collection_id`
- Output: `MatchResult(resource_ids, count, rule_version, warnings)`
- Pure read. No state. Idempotent.
- Returns empty list (not error) if no resources match

---

## 5. Transition to Phase 9

Phase 9 will build the Editorial Workflow on a **separate path**:

```
Phase 9 (Editorial)           |  Phase 8 (Rule) — FROZEN
──────────────────────────────┼─────────────────────────────
/admin/editorial.html         |  /admin/collection-detail.html
  (editorial completeness)    |    (rule debug tool)
                              |
/admin/editorial-edit.html    |  collection_rule_assist.py
  (write editor_note, etc.)   |    (rule creation CLI)
                              |
editorial_export.py           |  collection_dashboard_export.py
  (editorial-specific JSON)   |    (rule + collection data)
```

**No overlap. No coupling. Rule pages don't show editorial content. Editorial pages don't show rules.**

---

## 6. Sign-off

Phase 8 delivered a complete Rule Engine toolchain:

- Discovery → Gap → Review → Create → Simulate → Monitor
- All CLI-driven, zero backend services
- All data pre-computed via export, zero browser DB access
- Detail page cleaned and focused: answers "is this rule correct?" and nothing else
- Rule Engine has a documented, stable contract for Phase 9 to build upon

**Phase 8 is frozen. Phase 9 begins with Editorial Workflow.**

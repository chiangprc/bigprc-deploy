# Phase 8 — Rule Engine Architecture

> **Version**: v0.8-stable (Frozen)  
> **Date**: 2026-07-28  

---

## 1. Positioning

The Rule Engine determines **which resources belong to which collections**. It is a technical system, not a content system.

### Rule Engine is responsible for:
- Matching resources to collections via deterministic SQL
- Validating that rule_json produces correct results
- Providing evidence when rules are under-matching or over-matching
- Simulating rule changes before applying them
- Enforcing human confirmation on all rule modifications

### Rule Engine is NOT responsible for:
- SEO content (intro, seo_title, seo_desc, faq_json) — this is Content Layer
- Editorial curation (editor_note, why_collect, audience, highlights) — this is Editorial Layer
- Collection naming or topic discovery — this is Discovery Layer

### Architecture invariants
- Pure Python + SQL. **Zero AI in the matching hot path.**
- All read operations are cached via JSON export. No browser-to-DB connection.
- All write operations go through CLI with explicit YES confirmation.
- Rule schema is versioned and backward-compatible.

---

## 2. Rule Lifecycle

```
Stage 1: DISCOVERY
  Input:    resources + resource_tags (1760 items, 4500+ tags)
  Output:   Tag co-occurrence groups (JSON array)
  Script:   collection_discovery.py --scan --json
  Purpose:  Find recurring tag patterns that might form new collections

Stage 2: GAP ANALYSIS
  Input:    Discovery output + existing collection rule_json
  Output:   Classified groups (KEEP / EXPAND_RULE / NEW_COLLECTION / MERGE_REVIEW)
  Script:   collection_gap.py --analyze --json
  Purpose:  Tell the editor which patterns are already covered and which are new

Stage 3: IMPACT PREVIEW
  Input:    Current rule_json + proposed changes
  Output:   Before/after resource counts, delta, sample resource titles
  Script:   collection_rule_assist.py --preview <group_id>
  Purpose:  Show the editor what this rule would match before creating a draft

Stage 4: SIMULATION
  Input:    Existing collection rule_json + modifications (--add-tags, --add-tags-or, --rule)
  Output:   Added/removed resource lists with sample titles
  Script:   collection_rule_assist.py --simulate <id> ...
  Purpose:  Let the editor experiment with rule changes without writing to DB

Stage 5: PROPOSAL
  Input:    Editor-approved rule_suggestion
  Output:   Draft JSON file in collection_drafts/
  Script:   collection_rule_assist.py --propose <group_id>
  Purpose:  Generate an editable draft that the editor can review and modify

Stage 6: APPLY
  Input:    Draft JSON (possibly modified by editor)
  Output:   collections table INSERT + resource_collections population
  Script:   collection_rule_assist.py --apply <slug>
  Purpose:  Write the rule to the database. Requires typing "YES" to confirm.

Stage 7: MONITOR
  Input:    collections + resource_collections + rule_json
  Output:   Gap evidence, health status, quality tier, stability delta
  Scripts:  collection_dashboard_export.py, collection_health.py,
            collection_quality_report.py, collection_strategy_report.py
  Display:  /admin/collection-detail.html, /admin/dashboard.html,
            /admin/collections.html
  Purpose:  Continuously verify that rules are producing correct results
```

---

## 3. Architecture Principles

| # | Principle | Implementation |
|---|-----------|---------------|
| 1 | **Rule / Content / Editorial separation** | Three independent layers with distinct schemas, tools, and admin pages |
| 2 | **Action First** | Every gap, health issue, or delta comes with a specific recommended CLI command |
| 3 | **Read Only by Default** | All admin pages are static HTML. No browser can write to the database |
| 4 | **Simulate Before Apply** | All rule changes must be previewed before they can be applied |
| 5 | **Human In The Loop** | No automatic rule creation. Editor reviews, editor confirms |
| 6 | **Deterministic Matching** | `match_collection()` uses pure SQL. No ML model, no AI in the hot path |
| 7 | **Zero AI in Rule Engine** | AI suggests tags in Discovery. It does not write rules |
| 8 | **Backward Compatible** | New rule_json fields are additive. Existing rules never break on engine upgrade |
| 9 | **Evidence, Not Answers** | Gap analysis shows "which tags appear on missing resources" not "add these tags" |
| 10 | **CLI → JSON → Static HTML** | All data passes through this pipeline. No direct DB access from browser |

---

## 4. File Responsibility

### Rule Layer (Phase 8)
| File | Responsibility |
|------|---------------|
| `rule_engine.py` | Rule parsing + SQL matching. The single source of truth for "does this resource match this rule" |
| `collection_rule_assist.py` | Editor CLI for rule lifecycle: preview, propose, simulate, apply |
| `collection_discovery.py` | Tag co-occurrence pattern scanner (input to rule creation) |
| `collection_gap.py` | Coverage gap analyzer (classifies discovery groups vs. existing rules) |
| `collection_health.py` | Automated health checks: empty, thin, dead_rule, overlap |
| `collection_quality_report.py` | Quality tier classification: CORE/SOLID/NICHE/THIN/EMPTY |
| `collection_strategy_report.py` | Homepage ranking, parent-child analysis, stability tiers |
| `collection-detail.html` | Rule Debug Tool. Answers: "Is this rule correct? How do I fix it?" |
| `collection-review.html` | Discovery Review panel. Answers: "Which findings should I act on?" |

### Dashboard Layer (Phase 6)
| File | Responsibility |
|------|---------------|
| `collection_dashboard_export.py` | Generates dashboard.json, collections.json, collection-details.json |
| `dashboard.html` | Editorial workspace home: summary stats, health, recent findings |
| `collections.html` | Collection list with search, sort, filter |

### Content Layer (Phase 3-6)
| File | Responsibility |
|------|---------------|
| `collection_generator.py` | Creates resource_collections associations from COLLECTION_DEFS |
| `collection_faq.py` | AI generates FAQ JSON for collection_content |
| `collection_editor_ai.py` | AI generates editorial content (intro, seo, editor_note, etc.) |
| `ai_seo_writer.py` | AI generates tagline, summary, keywords for individual resources |
| `ai_tag_generator.py` | AI extracts structured tags from resource metadata |

### Editorial Layer (Phase 9 — Not Started)
| File | Responsibility |
|------|---------------|
| `EDITORIAL_MODEL.md` | Design document for editorial field definitions |
| `editorial.html` (future) | Editorial completeness dashboard |
| `editorial-edit.html` (future) | Editorial content editor |

---

## 5. Phase Boundary

```
Phase 8 Ends Here.

The Rule Engine is frozen. Its contract is:

  - parse_rule(rule_json) → SQL conditions
  - match_collection(cursor, rule_json) → resource_ids
  - rule_json schema: {tags, tags_or, cats, exclude_tags, min_resources, version}
  - All matching is deterministic. No AI. No auto-modification.

Future changes to the Rule Engine require:

  1. A written RFC describing the proposed change
  2. Assessment of backward compatibility with existing rule_json
  3. Update to parse_rule() contract documentation
  4. Validation that all 16 existing rules continue to match correctly

Phase 9 will build the Editorial Workflow on a separate, independent path.
```

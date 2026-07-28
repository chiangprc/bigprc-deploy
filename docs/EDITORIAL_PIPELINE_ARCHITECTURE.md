# Editorial Pipeline Architecture — v0.9.2

> **Version**: v0.9.2-stable (Frozen)  
> **Date**: 2026-07-29  

---

## 1. Architecture Overview

The Editorial Pipeline generates curatorial content for BigPRC collections. It is the third layer in a three-layer architecture:

```
Layer 1: Rule Engine (v0.8-stable)
  → Determines which resources belong to which collections
  → Pure SQL + Python. Zero AI.

Layer 2: Content (Phase 6 Stable)
  → Generates SEO/info content: intro, seo_title, seo_desc, faq_json
  → AI-generated, auto-publish with batch audit

Layer 3: Editorial (v0.9.2-stable)
  → Generates curatorial content: editor_note, why_collect, audience, highlights
  → AI-generated draft, human approval required
  → This document describes Layer 3
```

---

## 2. Complete Data Flow

```
resources (1760 items)
  │
  ├──> resource_tags (4500+ tags)
  │
  ▼
Rule Engine (rule_engine.py)
  │  parse_rule(rule_json) → SQL WHERE clause
  │  match_collection(cursor, rule_json) → resource_ids
  │
  ▼
collections (16 collections with rule_json)
  │
  ▼
collection_dashboard_export.py
  │  build_collection_details()
  │  → collection-details.json
  │
  ├─────────────────────────────────────────┐
  │                                         │
  ▼                                         ▼
collection_editor_ai.py --content      collection_editor_ai.py --editorial
  │                                         │
  │  generate_content()                     │  generate_editorial()
  │  ├─ intro                               │  ├─ editor_note prompt
  │  ├─ seo_title                           │  ├─ why_collect prompt
  │  ├─ seo_desc                            │  ├─ audience prompt
  │  └─ faq_json                            │  └─ highlights prompt
  │                                         │       │
  │  ai_call() ×1                           │  ai_call() ×4
  │  temperature=0.5                        │  temperature=0.7
  │  auto-publish                           │  draft only
  │                                         │       │
  │                                         │       ▼
  │                                         │  parse_highlights()
  │                                         │  ├─ Level 1: json.loads()
  │                                         │  ├─ Level 2: auto-fix → json.loads()
  │                                         │  └─ Level 3: line parser
  │                                         │
  ▼                                         ▼
collection_content                       collection_content
  intro, seo_title, seo_desc, faq_json    editor_note, why_collect,
                                          audience, highlights
  │                                         │
  └──────────────┬──────────────────────────┘
                 │
                 ▼
         auto_generate.py
                 │
                 ▼
     /var/www/site/web/collection/*.html
                 │
                 ▼
              Nginx
                 │
                 ▼
          https://www.bigprc.com/collection/{slug}.html
```

---

## 3. Module Responsibilities

### Rule Engine (`rule_engine.py`)
- **Status**: Frozen (v0.8-stable). Not modified by Editorial Pipeline.
- **Role**: Provides `match_collection()` for content-aware generation. Not called during editorial generation — editorial uses pre-computed collection metadata.
- **Contract**: `parse_rule(rule_json) → SQL`, `match_collection(cursor, rule) → MatchResult`
- **Freeze rule**: No changes unless accompanied by an RFC.

### `ai_call()` — AI Transport Layer
- **Role**: Calls DeepSeek Chat API with `response_format={"type":"json_object"}`. On JSON failure, retries without `response_format` for raw text fallback.
- **Input**: prompt string, temperature, max_tokens
- **Output**: parsed JSON dict, or `{"_raw": text}` for fallback parsing, or None
- **Freeze rule**: Retry logic, temperature defaults, and timeout are stable. Do not change without Phase 9.x RFC.

### `generate_content()` — SEO Content Generator
- **Role**: Single API call → intro, seo_title, seo_desc, faq_json
- **Policy**: Auto-publish. Batch audit. Low risk.
- **Temperature**: 0.5 (factual, consistent)
- **CLI**: `--content` mode

### `generate_editorial()` — Editorial Content Generator
- **Role**: Four separate API calls → editor_note, why_collect, audience, highlights
- **Policy**: Draft only. Per-field human approval required. High risk.
- **Temperature**: 0.7 (varied, opinionated)
- **CLI**: `--editorial` mode
- **Domain inference**: Prompts instruct the model to infer the collection domain from title + description + samples, and stay within it.
- **Freeze rule**: Prompt structure (4 separate calls, one per field) is stable. Prompt text may iterate.

### `parse_highlights()` — Multi-Level Parser
- **Level 1**: `json.loads()` — standard JSON array
- **Level 2**: Auto-fix common AI errors (trailing commas, missing commas, markdown fences, Chinese quotes, inline comments, extra prose), then `json.loads()` retry
- **Level 3**: Fallback line parser — strips JSON artifacts, extracts lines from markdown/numbered/bullet lists
- **Returns**: `(list[str] | None, label: str)` where label ∈ {JSON, Auto-fixed JSON, Fallback line parser, FAILED}
- **Freeze rule**: All three levels are stable. Only Level 2 auto-fix patterns or Level 3 artifact stripping may be extended.

### CLI
```
python3 collection_editor_ai.py --content [id] [--force] [--limit N]
python3 collection_editor_ai.py --editorial [id] [--force] [--dry-run] [--limit N]
```
- `id`: Single collection slug (optional — if omitted, all collections)
- `--force`: Overwrite existing content
- `--dry-run`: Preview without writing to database
- `--limit N`: Process maximum N collections
- **Freeze rule**: CLI flags and semantics are stable.

### Dry-run
- **Role**: Always generates and prints preview, even when content already exists
- **Behavior**: Never writes to database. Prints full editor_note/why_collect/audience/highlights. Shows parser source.
- **Output format**: `🧪 DRY RUN` header, `📄 已有内容 (数据库未修改)` if existing, `── Preview ──` with all four fields.
- **Freeze rule**: Output format is stable.

### Retry & Fallback
- `ai_call()`: JSON mode failure → retry without `response_format` → raw text wrapper `{"_raw": text}`
- `generate_editorial()`: handles both normal `data[name]` and `_raw` fallback wrapper
- `parse_highlights()`: receives raw text from fallback via Level 3
- Highlights failure does NOT kill the entire collection — editor_note, why_collect, audience succeed independently
- **Freeze rule**: Retry chain is stable.

### Parser Summary
- Tracks per-collection parser source
- Printed at end of run: `── Parser Summary ──`
- Labels: JSON, Auto-fixed JSON, Fallback line parser, FAILED
- **Freeze rule**: Summary format is stable.

---

## 4. Frozen Interfaces (Do Not Modify Without RFC)

| Interface | Frozen Since | Change Requires |
|-----------|-------------|----------------|
| `rule_engine.match_collection()` | v0.8 | RFC |
| `rule_engine.parse_rule()` | v0.8 | RFC |
| `ai_call()` retry chain | v0.9.1b | RFC |
| `parse_highlights()` Level 1-2 | v0.9.1c | RFC |
| CLI flags (`--content`, `--editorial`, `--dry-run`, `--force`) | v0.9.1b | RFC |
| Dry-run output format | v0.9.1b | RFC |
| `collection_content` schema | Phase 6 | Migration |
| Editorial prompt structure (4 separate calls) | v0.9.1b | RFC |
| Domain inference approach (prompt-based, not hardcoded) | v0.9.2 | RFC |

---

## 5. Known Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|-----------|
| AI output is stochastic | Same prompt may produce English or Chinese, different lengths, different tone | Retry on failure; Fallback parser for highlights; dry-run for preview before write |
| No content versioning | Cannot compare editor_note v1 vs v2 | Draft files in `collection_drafts/` serve as informal history |
| No per-field approval workflow | All 4 editorial fields are written or none | `--dry-run` preview; `--force` overwrite |
| No batch editorial review UI | Editor must review in terminal | Phase 9.3 will address this |
| English prompt → occasional English output | ~1/16 chance of English editor_note | Retry the specific collection; prompt improvement in Phase 9.x |
| Highlights parser Level 3 is lossy | May lose specific resource reference formatting | Level 1-2 handle 90%+ of cases; Level 3 is safety net |
| No AI cost tracking | Unknown token consumption per run | Not a product requirement; acceptable at current scale |

---

## 6. Phase 9.3 Development Plan

### Priority Order

| # | Item | Type | Goal | Modules | Est. Work | Success Criteria |
|---|------|------|------|---------|-----------|-----------------|
| 1 | **Editorial Dashboard** | New Page | Show editorial completeness for all 16 collections at a glance | `editorial.html`, `collection_dashboard_export.py` (+editorial_status) | ~150 lines | Editor opens dashboard, sees which collections lack which fields |
| 2 | **Editorial Editor** | New Page | Text areas for writing/reviewing editor_note, why_collect, audience, highlights per collection | `editorial-edit.html`, CLI `editorial_save.py` | ~200 lines | Editor can review and approve per-field without terminal |
| 3 | **Frontend Integration** | Template | Editorial fields automatically appear on `/collection/{slug}.html` | `collection.html` (already has `{% if %}` blocks) | ~5 lines (verify only) | Frontend visitors see editorial content |
| 4 | **Batch Editorial Audit** | Workflow | Run `--editorial --dry-run` for all collections, export report as JSON, load in dashboard | `editorial_export.py` | ~80 lines | Editor can audit all 16 in browser before deciding which to publish |

### Priority 1: Editorial Dashboard (`/admin/editorial.html`)

**Goal**: Editor opens one page and sees: which collections have complete editorial content, which are missing fields, which need review.

**Data**: New `editorial.json` exported by `collection_dashboard_export.py` (or a separate `editorial_export.py`). Contains per-collection editorial_status dict (has_intro, has_seo, has_faq, has_editor_note, has_why_collect, has_audience, has_highlights, pct_complete).

**Display**: Table with green/red dots per field, overall completion %, link to editorial-edit page.

**Work**: ~150 lines (new HTML + JS, ~30 lines export addition).

### Priority 2: Editorial Editor (`/admin/editorial-edit.html?id=`)

**Goal**: Editor can read and approve editorial content per collection without using terminal.

**Data**: Reads `editorial.json` or `collection-details.json`. Writes via CLI (`editorial_save.py --collection bbc-nature --field editor_note --value "..."`).

**Display**: Four text areas pre-filled with current content (or placeholder if empty). Each field has an [Approve] button. No auto-save.

**Work**: ~200 lines (new HTML + JS + ~50 line CLI save script).

### Priority 3: Frontend Integration

**Goal**: Editorial content appears on public-facing collection pages.

**Status**: `collection.html` template already has `{% if editor_note %}`, `{% if why_collect %}`, `{% if audience %}`, `{% if highlights %}` blocks from Phase 4.x design. Once fields are populated in `collection_content`, content automatically renders.

**Work**: Verify only. No code changes expected.

### Priority 4: Batch Editorial Audit

**Goal**: Run `--editorial --dry-run` across all collections, output structured JSON report for dashboard review.

**Data**: New `editorial_export.py` that wraps `collection_editor_ai.py --editorial --dry-run` output into `editorial-audit.json`.

**Display**: Dashboard loads `editorial-audit.json` and shows per-collection preview text.

**Work**: ~80 lines.

---

## 7. Architecture Invariants (Carry Forward)

From Phase 6/7/8, reaffirmed:

1. **CLI → JSON → Static HTML** — All admin pages remain static
2. **No browser-to-DB connection** — All data passes through pre-generated JSON
3. **No server runtime** — No Node, FastAPI, PHP, or Flask
4. **Writes go through CLI** — `editorial_save.py` for content writes
5. **Rule Engine frozen** — Editorial Pipeline does not modify rule_json or matching logic
6. **Content/Editorial decoupled** — Content (auto-publish) and Editorial (human approval) have separate pipelines, policies, and risk levels

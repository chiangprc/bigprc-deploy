# Phase 10.10.1 — Editorial Production Pipeline Audit

> Audit only. Assess readiness for 500-resource scale.

---

## 1. `editorial_pilot.py` — Code Review

### What Works

| Component | Status | Notes |
|-----------|--------|-------|
| Guideline Check | ✅ | 8 forbidden phrases + audience + length + counts validation |
| DB write guard | ✅ | Only writes if `editorial_status IS NULL` — prevents overwrite |
| Resource selection | ✅ | Priority: spotlight → CORE → SOLID, randomized within tier |
| JSON serialization | ✅ | `ensure_ascii=False` for Chinese text |
| Export for admin UI | ✅ | `--export` writes `editorial-pending.json` |
| Report statistics | ✅ | `--report` shows status distribution + avg lengths |
| CLI usability | ✅ | Separate flags for each operation, clear help text |

### Gaps — Must Fix Before Scale

| # | Gap | Severity | Fix |
|---|-----|----------|-----|
| G1 | `generate_editorial()` is a stub — raises `NotImplementedError` | 🔴 P0 | Implement real AI API call using the prompt from Phase 10.9.2 |
| G2 | `get_pilot_resources()` only selects NULL status — can't regenerate rejected resources | 🟡 P1 | Add `--force` flag to allow regeneration for rejected |
| G3 | No batch publish — `--publish` takes a single ID | 🟡 P1 | Add `--publish-batch` or accept multiple IDs |
| G4 | No `--tier` filter for generate (CORE/SOLID/NICHE) | 🟡 P1 | Add tier filter for scale generation |
| G5 | No retry on API failure — single resource failure stops batch | 🟡 P1 | Wrap in try/except, continue on individual failures |

### Gap Details

**G1 — AI stub**: This is the blocking issue. The `generate_editorial()` function must be implemented with the actual AI API call. Reference `ai_seo_writer.py` for the API pattern — same endpoint, different system prompt.

**G2 — Regeneration**: If a reviewer rejects a resource (status = 'rejected'), there's no way to regenerate it. The `get_pilot_resources()` query filters `WHERE editorial_status IS NULL`, so rejected resources are invisible. Need a `--force` flag or a separate `--regenerate` command.

**G3 — Batch publish**: With 500 resources, publishing one at a time is impractical. Need `--publish-batch` that accepts multiple IDs or a file.

**G4 — Tier filter**: The scale plan needs `--tier CORE` and `--tier SOLID` to generate by quality tier. Current query has tier logic in ORDER BY but no filter.

**G5 — Error resilience**: If the AI API fails on resource #37 of 50, the entire batch stops. Need per-resource try/except with a failure counter.

---

## 2. Editorial Review Workflow — Audit

### Current State

```
editorial_pilot.py --generate  →  writes draft to DB
editorial_pilot.py --export    →  writes JSON for admin UI
/admin/editorial-review.html   →  displays pending queue (read-only)
editorial_pilot.py --publish   →  marks as published (CLI only)
```

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| W1 | Review page is read-only — no inline edit capability | P2 |
| W2 | No "approve to reviewed" action (only publish to published) | P1 |
| W3 | Publish is CLI-only — no web action button | P2 |
| W4 | No audit trail for who published/rejected when | P2 |

**Assessment**: The workflow is functional for a single editor. Gaps W2-W4 are P2 — acceptable for now. The CLI/Admin split (review in browser, action in CLI) is intentional for a single-operator workflow.

---

## 3. EQS Scoring — Audit

### Current State

EQS is a **manual rubric** defined in `PHASE10_8_9_QUALITY_CALIBRATION.md`. It has:
- 5 dimensions with 1-5 scale
- Clear scoring rules (≥20 APPROVE, etc.)
- Example calibrations
- Reviewer checklist

### Gaps

| # | Gap | Severity |
|---|-----|----------|
| E1 | EQS is paper-only — not stored in database | P2 |
| E2 | No automated EQS component (all dimensions require human judgment) | — (by design) |
| E3 | No inter-reviewer calibration (single editor — not an issue yet) | P3 |

**Assessment**: EQS is adequate for the current single-editor workflow. Adding EQS fields to the database would be premature optimization.

---

## 4. Data Model Risk Assessment

### Current Schema

```
resources table:
  editor_recommendation TEXT
  target_audience TEXT
  strengths TEXT (JSON)
  caveats TEXT (JSON)
  editorial_status TEXT (draft/reviewed/published/rejected)
  reviewed_at TEXT
  generated_at TEXT
  ai_model TEXT
```

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| JSON parse failure on strengths/caveats | Low | Medium | Guideline check validates JSON before write |
| editorial_status values diverge from enum | Low | Low | Application-layer enum; CLI enforces valid values |
| NULL status + published content mismatch | Low | High | Template guard `{% if editorial_status == 'published' %}` |
| Database size bloat from 500 new text rows | Very Low | Low | 500 × ~500 bytes = ~250KB — negligible for SQLite |

**Assessment**: No data model changes needed for scale. The 8-column schema is adequate for 500+ resources.

---

## 5. Scale Readiness Assessment

### Go/No-Go Checklist

| # | Condition | Status |
|---|-----------|--------|
| 1 | AI generation function implemented | 🔴 P0 — Blocking |
| 2 | Guideline Check automated | ✅ Ready |
| 3 | Admin review page functional | ✅ Ready |
| 4 | Publish workflow tested | ✅ Ready (CLI) |
| 5 | Resource selection by tier | 🟡 P1 — Need filter |
| 6 | Batch failure resilience | 🟡 P1 — Need try/except |
| 7 | Batch publish support | 🟡 P1 — Need multi-ID |
| 8 | EQS rubric defined | ✅ Ready |
| 9 | Prompt optimized (10.9.2) | 🟡 P1 — Need A/B test |
| 10 | Reject mechanism functional | ✅ Ready |

### Verdict

**NOT READY for 500-resource scale.** 1 P0 blocker (AI function) + 4 P1 gaps must be resolved first.

### Recommended Actions (in order)

1. **Implement `generate_editorial()`** — connect to AI API (P0, ~30 min)
2. **Run A/B prompt test** — validate revised prompt from 10.9.2 (P1, ~1 hour)
3. **Add `--tier` filter + `--publish-batch`** — CLI enhancements (P1, ~30 min)
4. **Add per-resource error handling** — try/except in generation loop (P1, ~15 min)
5. **Test with 10 resources** — end-to-end validation
6. **Scale to 50, then 100, then 500** — incremental

---

## 6. Trust Layer Readiness (P2)

### `/curation` page

**Not yet created.** The Phase 10.8 Framework proposed it; Phase 10.10 P2 calls for it.

Design requirements:
- Single static page explaining BigPRC's curation standards
- Linked from resource detail pages ("了解策展标准 →")
- Linked from footer
- Minimal design — reuse existing .card/.ed-panel tokens
- Content from PHASE10_8_EDITORIAL_FRAMEWORK.md §4

**Assessment**: Low effort. Create as a static HTML page in `root/custom-pages/curation.html`.

### Trust signals on resource pages

Already designed in Phase 10.8.4:
- "收录于 YYYY-MM" — uses `created_at` from DB
- "链接验证于 YYYY-MM" — uses `last_checked` if available
- "了解策展标准 →" — links to `/curation`

**Assessment**: Requires minor template changes to `detail.html`. Defer to Phase 10.10.2.

---

## 7. Summary

| Component | Score | Status |
|-----------|-------|--------|
| Generation script | 7/10 | P0 stub + 4 P1 gaps |
| Review workflow | 8/10 | Functional, CLI publish is acceptable |
| EQS rubric | 9/10 | Complete, just not automated |
| Data model | 9/10 | Adequate, no changes needed |
| Scale readiness | 5/10 | **Not ready** — resolve P0+P1 first |
| Trust layer | 2/10 | Not yet built |

### Priority Actions

```
P0: Implement AI generation function          ← BLOCKING
P1: A/B prompt test                           ← before scale
P1: CLI enhancements (tier/batch/retry)       ← before scale
P1: End-to-end 10-resource test               ← validation gate
P2: /curation page + trust signals            ← after scale
```

---

> **Pipeline audit complete. Scale blocked on P0 (AI stub) + 4 P1 gaps.**
> **Recommended: resolve P0+P1, test with 10 resources, then proceed to scale.**

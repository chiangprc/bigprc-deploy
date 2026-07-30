# Phase 10.10.3 — Editorial Production Validation

> Validate quality before scaling. Prove the engine works.

---

## Step 1 — Prompt A/B Evaluation

### Setup

```bash
# Generate 10 with Prompt A (Differentiation focus)
python3 editorial_pilot.py --generate --tier core --limit 10 --prompt A

# Generate 10 with Prompt B (Editorial Voice focus)
python3 editorial_pilot.py --generate --tier core --limit 10 --prompt B

# Export for review
python3 editorial_pilot.py --export /var/www/site/web/admin/data/editorial-pending.json
```

### A/B Scoring Template

For each of the 20 resources, score EQS 1-5 on five dimensions:

| Resource | Prompt | Spec | Aud | Diff | Hon | Voice | Total | Decision |
|----------|--------|------|-----|------|-----|-------|-------|----------|
| 1 | A | | | | | | | |
| 2 | A | | | | | | | |
| ... | | | | | | | | |
| 11 | B | | | | | | | |
| ... | | | | | | | | |

### Winner Criteria

Compare average scores:

| Dimension | Prompt A Avg | Prompt B Avg | Winner |
|-----------|-------------|-------------|--------|
| Specificity | | | |
| Audience Fit | | | |
| Differentiation | | | |
| Honesty | | | |
| Editorial Voice | | | |
| **Total** | | | |

Adopt the winning prompt for production use.

---

## Step 2 — 50 CORE Production Test

### Command

```bash
python3 editorial_pilot.py --generate --tier core --limit 50 --prompt <WINNER>
```

### Flow

```
[generate 50] → [Guideline Check] → [DB write (draft)]
                                        ↓
[export JSON] → [/admin/editorial-review.html]
                                        ↓
[human EQS review] → [APPROVE/REVISE/REJECT]
                                        ↓
[--publish ID1 ID2...] → [published → live on site]
```

### Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| JSON parse success rate | >95% | TBD |
| Guideline Check pass rate | >90% | TBD |
| Avg EQS | ≥18 | TBD |
| APPROVE rate (EQS ≥20) | >60% | TBD |
| REVISE rate (EQS 15-19) | <30% | TBD |
| REJECT rate (EQS <15) | <10% | TBD |
| Avg generation time/resource | <15s | TBD |

---

## Step 3 — Production Metrics Dashboard

### Command

```bash
python3 editorial_pilot.py --metrics
```

### Dashboard Output

```
=== Editorial Production Metrics ===
Total generated:     50
  Draft:             0
  Reviewed:          12
  Published:         35
  Rejected:          3
  Publish rate:      70%
  Reject rate:       6%
Avg rec length:      118 chars
Avg audience length: 42 chars
Avg strengths:       2.6
Avg caveats:         2.1
Model usage:
  gpt-4o: 48
  gpt-4o-mini: 2

Quality Alerts:
  (none if all thresholds met)
```

### Threshold Alerts

The dashboard automatically flags:
- Publish rate < 50%
- Reject rate > 10%
- Avg recommendation < 40 chars
- Avg strengths < 2.0
- Avg caveats < 1.0

---

## Step 4 — Go/No-Go Decision

### Acceptance Criteria

| # | Criterion | Method | Threshold |
|---|-----------|--------|-----------|
| 1 | JSON success rate | `--metrics` | >95% |
| 2 | Guideline pass rate | Generation log | >90% |
| 3 | Average EQS | Human review | ≥18 |
| 4 | Reject rate | `--metrics` | <10% |
| 5 | Human revision rate | Review notes | <30% |

### Decision

- **All 5 criteria met**: GO → Phase 10.10.4 (Scale 50→100→500)
- **4/5 met**: CONDITIONAL GO → fix the failing criterion, re-test 20 resources
- **<4/5 met**: NO-GO → return to Phase 10.9.2 (Prompt optimization)

---

## Production Commands Reference

```bash
# A/B test
python3 editorial_pilot.py --generate --tier core --limit 10 --prompt A
python3 editorial_pilot.py --generate --tier core --limit 10 --prompt B

# Production generation
python3 editorial_pilot.py --generate --tier core --limit 50

# Review workflow
python3 editorial_pilot.py --export /var/www/site/web/admin/data/editorial-pending.json
python3 editorial_pilot.py --review

# Batch publish
python3 editorial_pilot.py --publish id1 id2 id3 ...

# Metrics dashboard
python3 editorial_pilot.py --metrics

# Full report
python3 editorial_pilot.py --report
```

---

> **Validation framework ready. VPS execution required for AI generation.**
> **All 5 acceptance criteria must pass before Phase 10.10.4 (Scale).**

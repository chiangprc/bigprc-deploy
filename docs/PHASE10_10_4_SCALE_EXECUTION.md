# Phase 10.10.4 — Editorial Scale Execution

> Controlled scale: 100 → quality gate → 500. Quality over coverage.

---

## Step 1 — Prompt Winner Selection

### Execution

```bash
python3 editorial_pilot.py --generate --tier core --limit 10 --prompt A
python3 editorial_pilot.py --generate --tier core --limit 10 --prompt B
python3 editorial_pilot.py --export /var/www/site/web/admin/data/editorial-pending.json
```

### Evaluation Matrix (human review)

| # | Resource | Prompt | Spec | Aud | Diff | Hon | Voice | Total |
|---|----------|--------|------|-----|------|-----|-------|-------|
| A1-A10 | 10 resources | A | /5 | /5 | /5 | /5 | /5 | /25 |
| B1-B10 | 10 resources | B | /5 | /5 | /5 | /5 | /5 | /25 |

### Winner Selection

```
Prompt A avg EQS: ___ / 25
Prompt B avg EQS: ___ / 25
Winner: Prompt ___
```

Declare the production prompt and document the decision.

---

## Step 2 — 100-Resource Scale Batch

### Batch Plan

| Batch | Tier | Count | Command |
|-------|------|-------|---------|
| 1 | spotlight | ~10 | `--tier spotlight --limit 10` |
| 2 | CORE | 30 | `--tier core --limit 30` |
| 3 | CORE | 30 | `--tier core --limit 30` |
| 4 | SOLID | 30 | `--tier solid --limit 30` |

### Execution Flow per Batch

```
1. python3 editorial_pilot.py --generate --tier <TIER> --limit <N>
   → generates N drafts, runs Guideline Check, writes to DB

2. python3 editorial_pilot.py --export /var/www/site/web/admin/data/editorial-pending.json
   → exports pending items for admin review UI

3. Open /admin/editorial-review.html
   → human reviews each item, scores EQS 1-5 × 5 dimensions

4. python3 editorial_pilot.py --publish <approved_ids>
   → publishes approved resources (status → published)

5. python3 editorial_pilot.py --metrics
   → check quality thresholds
```

### Skip Rules During Scale

```
Skip resource if:
  - title is generic / auto-generated (e.g., "新建文件夹")
  - seo_desc is empty (no context for AI to work with)
  - resource has no collection assignment
  - resource is marked as low quality / broken
```

---

## Step 3 — Quality Gates

### Per-Batch Gate

After each batch is generated + reviewed, run:

```bash
python3 editorial_pilot.py --metrics
```

Check against thresholds:

| Gate | Threshold | Action if Failed |
|------|-----------|-----------------|
| Guideline pass rate | >90% | Pause, review failed prompts, adjust AI parameters |
| Reject rate | <10% | If >10%: review rejected samples, identify pattern |
| Avg recommendation length | >40 chars | If shorter: prompt is producing truncated output |
| Avg strengths count | ≥2.0 | If lower: AI is being lazy — tighten prompt |
| Avg caveats count | ≥1.0 | If lower: AI is skipping limitations — emphasize in prompt |

### Gate Failure Protocol

```
1. Pause generation (do not start next batch)
2. Sample 5 failures from the failing batch
3. Identify root cause (prompt / model / data quality)
4. Fix and re-test with 5 resources
5. If fixed: resume batch from where it stopped
6. If not fixed after 2 attempts: escalate to Prompt Optimization (10.9.2)
```

---

## Step 4 — Metrics Extension

### Enhanced `--metrics` Output

After 100 resources:

```
=== Editorial Production Metrics ===
Generation:
  Total generated:     100
  JSON success rate:   97% (3 failures)
  Avg gen time:        8.2s/resource

Quality:
  Draft:               0
  Reviewed:            15
  Published:           80
  Rejected:            5
  Publish rate:        80%
  Reject rate:         5%

Content:
  Avg rec length:      124 chars
  Avg audience length: 45 chars
  Avg strengths:       2.7
  Avg caveats:         2.0

EQS (human review):
  Average EQS:         19.5 / 25
  APPROVE (≥20):       62%
  REVISE (15-19):      28%
  REJECT (<15):        10%

Model:
  gpt-4o:              97 generations (97%)
  gpt-4o-mini:         3 generations (3%, fallback)

Cost estimate:
  ~$0.15/resource (GPT-4o)
  ~$15.00 total for 100 resources

✅ All quality thresholds met.
```

### Trend Tracking

After 3+ batches, compare:

```
Batch 1 (30 CORE):  EQS avg 18.2, reject 8%
Batch 2 (30 CORE):  EQS avg 19.1, reject 6%
Batch 3 (30 SOLID): EQS avg 19.8, reject 5%
→ Quality trending up as prompt stabilizes ✅
```

---

## Step 5 — Go/No-Go to 500

### Decision Criteria (after 100 resources)

| # | Criterion | Threshold | Actual |
|---|-----------|-----------|--------|
| 1 | JSON success rate | >95% | |
| 2 | Guideline pass rate | >90% | |
| 3 | Avg EQS | ≥18 | |
| 4 | Reject rate | <10% | |
| 5 | Publish rate | >70% | |

### Decision

```
All 5 met:  GO → scale to 500 (Phase 10.10.5)
4/5 met:    CONDITIONAL → fix failing criterion, re-test 30
<4 met:     NO-GO → return to Prompt Optimization
```

---

## Principle (reconfirmed)

> BigPRC's editorial layer does not aim for 100% resource coverage.
> It aims for 100% quality on the resources that matter most.
>
> A resource without an Editor's Take is neutral.
> A resource with a bad Editor's Take damages trust.
>
> Quality over coverage. Always.

---

> **Scale execution plan ready. VPS execution required.**
> **5 quality gates must pass before proceeding to 500.**

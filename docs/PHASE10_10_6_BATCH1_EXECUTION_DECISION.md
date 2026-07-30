# Phase 10.10.6 — Batch 1 Execution & Decision

> First real editorial production batch. Prove the engine.

---

## Execution Steps (VPS)

### Step 1 — Generate (A/B)

```bash
cd /root/bigprc-deploy
git pull origin main
bash deploy.sh

# A/B test: 10 each
python3 editorial_pilot.py --generate --tier spotlight --limit 10 --prompt A
python3 editorial_pilot.py --generate --tier spotlight --limit 10 --prompt B
```

Expected: 20 drafts in DB. Check `--report` for counts.

---

### Step 2 — Export for Review

```bash
python3 editorial_pilot.py --export /var/www/site/web/admin/data/editorial-pending.json
```

Open: `https://www.bigprc.com/admin/editorial-review.html`

---

### Step 3 — EQS Scoring

For each of the 20 resources, fill in the scorecard from `PHASE10_10_5_BATCH1_QUALITY_REPORT.md`:

```
Specificity      /5  — Does it mention versions, dates, concrete features?
Audience Fit     /5  — Is the target user specific, not "everyone"?
Differentiation  /5  — Does it explain why THIS version/choice?
Honesty          /5  — Are caveats real and specific?
Editorial Voice  /5  — Does it read like a human editor, not AI?
```

Decision per resource:
```
≥20: APPROVE → ready to publish
15-19: REVISE → minor edits needed
<15: REJECT → regenerate or skip
```

---

### Step 4 — Prompt Winner

Compare Prompt A (Differentiation) vs Prompt B (Editorial Voice):

| Metric | A | B | Winner |
|--------|---|---|--------|
| Avg EQS | | | |
| Voice avg | | | |
| APPROVE rate | | | |
| REJECT rate | | | |

**Decision**: Production Prompt = ___

---

### Step 5 — Publish Approved

```bash
# Publish all APPROVE resources from the winning prompt
python3 editorial_pilot.py --publish <id1> <id2> ...
```

Verify on live site: visit a published resource on `bigprc.com` — Editor's Take section should appear.

---

### Step 6 — Quality Gate Check

```bash
python3 editorial_pilot.py --metrics
```

| Gate | Threshold | Actual | Status |
|------|-----------|--------|--------|
| Guideline pass | >90% | __% | |
| Reject rate | <10% | __% | |
| Avg EQS | ≥18 | __ | |
| Avg rec length | >40c | __c | |
| Avg strengths | ≥2 | __ | |
| Avg caveats | ≥1 | __ | |

---

## Decision

```
[ ] ALL GATES PASSED
    → Proceed to Phase 10.11: CORE Scale (50→100 resources)

[ ] 5/6 GATES PASSED
    → Conditional. Fix failing gate. Re-test 10.

[ ] <5 GATES PASSED
    → NO-GO. Return to Prompt Optimization (Phase 10.9.2).
```

---

## Post-Decision Actions

### If GO:
```bash
# Scale to CORE
python3 editorial_pilot.py --generate --tier core --limit 50
# ... repeat review + publish cycle
```

### If NO-GO:
```bash
# Return to prompt work
# Edit PROMPT_A / PROMPT_B in editorial_pilot.py
# Re-run A/B with revised prompts
```

---

> **VPS execution required. Fill in metrics after real AI generation.**
> **The engine is ready. Now prove it works.**

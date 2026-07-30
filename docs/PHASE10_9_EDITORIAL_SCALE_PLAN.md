# Phase 10.9 — Editorial Scale & Automation

> From quality validation to controlled scale. Quality over coverage.

---

## Phase 10.9.1 — 100 Resource Final Review

### Review Data Collection

After 100 resources are reviewed using the EQS 5-dimension rubric:

```
python3 editorial_pilot.py --report
```

Expected output metrics:

| Metric | Current (50) | Target (100) |
|--------|-------------|--------------|
| Total with editorial | 50 | 100 |
| Published | TBD | ≥ 70 |
| Reviewed (awaiting publish) | TBD | ≥ 15 |
| Draft | TBD | ≤ 10 |
| Rejected | 0 | ≤ 5 |
| Avg EQS | TBD | ≥ 18 |
| Avg recommendation length | ~120 chars | 80-150 chars |
| Avg strengths count | ~2.5 | 2-3 |
| Avg caveats count | ~2.0 | 1-3 |

### APPROVE / REVISE / REJECT Ratio

```
APPROVE (EQS ≥ 20):  ████████████  ~60%  → publish immediately
REVISE (EQS 15-19):  ██████        ~25%  → minor edits → publish
REWRITE (EQS 10-14): ███           ~10%  → regenerate
REJECT (EQS < 10):   █             ~5%   → mark rejected
```

### High-Frequency Failure Analysis

From REVISE + REWRITE + REJECT, categorize root causes:

| Root Cause | Frequency | Fix |
|-----------|-----------|-----|
| Audience too generic ("适合需要XX的用户") | ~35% | Prompt: require specific user persona |
| No differentiation from alternatives | ~25% | Prompt: require explicit comparison |
| Caveats missing or too vague | ~20% | Prompt: require at least 2 specific limitations |
| Reads as AI template | ~15% | Prompt: editorial voice examples |
| Factual inaccuracy (version/dates) | ~5% | Human review only — AI can't fix |

---

## Phase 10.9.2 — Prompt Optimization

### Current Prompt Weaknesses (from 10.9.1 analysis)

**Issue 1**: AI defaults to "适合需要 XX 的用户" — generic audience.

**Fix**: Add audience taxonomy to system prompt:
```
target_audience 必须从以下类型中选择至少一种：
- 零基础入门（从未接触过该领域）
- 有基础进阶（了解基础，需要深入）
- 专业从业者（日常工作使用）
- 学生（在校学习需要）
- 内容创作者（制作内容发布）
- 开发者（编程/技术背景）
如果不属于以上任何类型，说明为什么不适合分类。
```

**Issue 2**: Recommendation doesn't differentiate from other versions.

**Fix**: Add explicit comparison requirement:
```
必须回答："与其他版本或替代选择相比，为什么推荐这个版本？"
如果没有其他版本，说明为什么这个资源是唯一的或稀缺的。
```

**Issue 3**: Caveats are filler rather than real limitations.

**Fix**: Add caveat prompting:
```
caveats 必须是用户在下载/使用前真正需要知道的信息。
不要写"需要一定基础"这种用在哪里都可以的表述。
如果确实没有限制，写清楚"无特殊限制"，不要编造。
但注意：几乎每个资源都有边界条件（系统要求、版本限制、
学习成本、适用场景边界）——找到它们。
```

### Revised System Prompt

```
你是 BigPRC 的数字资源策展编辑。
你的任务是帮助用户判断一个资源是否适合他们。

资源信息：
名称: {title}
类型: {category}
大小: {file_size}
平台: {platform}
版本: {version}
所属专题: {collections}
现有描述: {seo_desc}

写作要求：

1. editor_recommendation (1-3 句)
   告诉用户为什么这个资源值得花时间。
   必须包含至少一个具体细节（版本号、时间范围、内容特征）。
   必须说明与其他选择相比的特点——如果没有其他选择，说明为什么这个资源稀缺。

2. target_audience (1 句)
   必须从以下类型中选择至少一种，并具体化：
   零基础入门 / 有基础进阶 / 专业从业者 / 学生 / 内容创作者 / 开发者 / 家庭用户 / 教育者
   禁止写"所有人"或"每个人"。

3. strengths (2-3 条，每条 "+" 开头)
   必须是可验证的、具体的优势。
   禁止："功能强大" "非常优秀" "值得推荐" "强烈推荐" "必备" "神器" "全网最全" "最好用"

4. caveats (1-3 条，每条 "·" 开头)
   必须是用户在下载/使用前真正需要知道的信息。
   包括但不限于：系统要求、版本限制、学习成本、文件大小注意事项、适用场景边界。
   如果确实没有限制，写"无特殊限制"。但请再三确认。
   禁止编造不存在的限制。

格式（JSON）：
{
  "editor_recommendation": "...",
  "target_audience": "...",
  "strengths": ["+ ...", "+ ...", "+ ..."],
  "caveats": ["· ...", "· ..."]
}
```

### Prompt A/B Testing

Generate 20 resources with Current Prompt (A) and 20 with Revised Prompt (B).
Compare:

| Metric | Prompt A | Prompt B | Winner |
|--------|----------|----------|--------|
| Avg EQS | TBD | TBD | — |
| Audience specificity rate | TBD | TBD | — |
| Differentiation rate | TBD | TBD | — |
| Caveat quality rate | TBD | TBD | — |
| Forbidden phrase rate | TBD | TBD | — |

Adopt the winning prompt for scale generation.

---

## Phase 10.9.3 — Scale Expansion

### Scale Criteria (from Phase 10.8.9)

All conditions confirmed before scaling:

- [ ] EQS ≥ 15 for >80% of reviewed resources
- [ ] Reject rate <10%
- [ ] Forbidden phrase rate <2%
- [ ] Reviewer can process >20 resources/hour
- [ ] At least 3 different resource types achieve EQS ≥ 20
- [ ] Revised prompt validated (Phase 10.9.2 A/B test)

### Scale Targets

| Tier | Count | Priority | Batch Size |
|------|-------|----------|------------|
| Spotlight | ~20 | P0 — immediate | All |
| CORE collections | ~200 | P0 — immediate | 50/batch |
| SOLID collections | ~300 | P1 — within 1 week | 50/batch |
| NICHE collections | ~200 | P2 — as needed | On demand |
| EMPTY / unclassified | — | Skip | — |

**Total scale target**: ~500 resources with editorial content.

### Batch Processing

```bash
# Batch 1: All CORE resources
python3 editorial_pilot.py --generate --tier CORE
python3 editorial_pilot.py --export /var/www/site/web/admin/data/editorial-pending.json

# Review on /admin/editorial-review.html (20-30 min per batch of 50)
# Publish approved:
python3 editorial_pilot.py --publish <id1> <id2> ...

# Batch 2: SOLID batch 1
python3 editorial_pilot.py --generate --tier SOLID --limit 50
# ... repeat review + publish
```

### Quality Monitoring During Scale

After each batch of 50:
```
python3 editorial_pilot.py --report
→ Check: EQS avg, reject rate, forbidden phrase rate
→ If any metric degrades >10%: pause, investigate, fix prompt
```

### Content That Will NOT Get Editorial Layer

| Reason | Example | Action |
|--------|---------|--------|
| Pure utility | A single font file, a driver package | Skip — no editorial value |
| Self-explanatory | "Windows 11 24H2 ISO" — the title says everything | Skip — editorial would be noise |
| Low quality | Incomplete, broken, superseded | Skip — fix the resource first |
| Duplicate | Same software, older version | Skip — only the best version gets editorial |

---

## Scale Timeline

```
Week 1:
  Day 1: Confirm Go criteria (10.9.1 — 100-resource review)
  Day 2: Run A/B prompt test (10.9.2)
  Day 3: Adopt winning prompt, generate CORE batch 1 (50)
  Day 4: Review CORE batch 1, publish approved
  Day 5: Generate CORE batch 2 (50), review, publish

Week 2:
  Day 1-2: CORE batches 3-4 (100 resources)
  Day 3-5: SOLID batches 1-3 (150 resources)

Week 3:
  Day 1-3: SOLID batches 4-6 (150 resources)
  Day 4-5: Quality audit (random sample 50, re-score EQS)
  → Decision: continue to NICHE or maintain at ~500
```

---

## The Principle

> BigPRC's editorial layer does not aim for 100% coverage.
> It aims for 100% quality on the resources that matter most.
>
> A resource without an Editor's Take is not broken.
> A resource with a bad Editor's Take is broken.
>
> Quality over coverage. Always.

---

> **Scale plan complete. Awaiting Go/No-Go from 10.9.1 Final Review.**

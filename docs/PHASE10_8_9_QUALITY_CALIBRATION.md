# Phase 10.8.9 — Editorial Quality Calibration

> Quality scoring, expanded pilot, reject mechanism. No schema changes.

---

## 1. Editorial Quality Score (EQS)

### Five Dimensions

Each Editor's Take is scored 1-5 on five dimensions by the human reviewer.

| Dimension | 1 (Fail) | 3 (Pass) | 5 (Excellent) |
|-----------|----------|----------|---------------|
| **Specificity** | "这是一款优秀软件" | "Blender 3.0-4.0 全覆盖" | "前 10 集面向从没打开过 3D 界面的用户" |
| **Audience Fit** | "适合所有人" | "适合视频创作者" | "适合已从 Premiere 转到 Resolve、需要进阶的创作者" |
| **Differentiation** | 未提及任何比较 | 提及与其他版本的区别 | 明确指出为什么这个版本是最佳选择 |
| **Honesty** | 0 条 caveats | 1 条真实限制 | 2-3 条具体限制 + 替代建议 |
| **Editorial Voice** | 读起来像 AI 模板 | 有判断，但不突出 | 一句话就能认出来是 BigPRC 编辑 |

### Scoring Rules

```
Total Score = sum of 5 dimensions (max 25)

≥ 20: APPROVE — publish immediately
15-19: REVISE — minor edits needed, then publish
10-14: REWRITE — significant issues, regenerate
< 10: REJECT — resource not suitable for editorial layer
```

### Calibration Examples

**Score 23 — APPROVE** (DaVinci Resolve 教程):
```
Specificity:     5 — "Resolve 17+, Fusion 节点逻辑, 前 3 集已过期"
Audience Fit:    5 — "已从 Premiere/FCP 转 Resolve 的创作者"
Differentiation: 5 — "少数真正讲透 Fusion 和 Fairlight 的中文教程"
Honesty:         4 — 2 条 caveats, 但可以加一条关于总时长的
Editorial Voice: 4 — 读起来像真人编辑
```

**Score 16 — REVISE** (某通用软件):
```
Specificity:     3 — 提到了版本号但缺少内容范围
Audience Fit:    3 — "适合需要 XX 的用户" 太泛
Differentiation: 3 — 提及了与其他版本的区别但不够具体
Honesty:         4 — 2 条有效 caveats
Editorial Voice: 3 — 有一句"非常实用"需要删掉
→ 修改 forbidden phrase + 细化 audience → APPROVE
```

**Score 12 — REWRITE** (某资源):
```
Specificity:     2 — 没有任何具体版本/日期/范围
Audience Fit:    2 — "适合有兴趣的用户"
Differentiation: 2 — 未提及任何替代选择
Honesty:         3 — 1 条 caveat 但太泛 ("需要一定基础")
Editorial Voice: 3 — 平淡，没有判断
→ 整体太像 AI 描述，需要重新生成
```

**Score 7 — REJECT** (某重复资源):
```
Specificity:     1 — 完全泛泛
Audience Fit:    1 — "所有人"
Differentiation: 1 — 这个资源与专题内已有资源几乎相同
Honesty:         2 — 无 caveats
Editorial Voice: 2 — 无法判断
→ 与已有资源重复，不单独写 Editor's Take
```

---

## 2. Expanded Pilot — 100 Resources

### Selection (50 existing + 50 new)

| Collection | Type | Existing | New | Total |
|-----------|------|----------|-----|-------|
| bbc-nature | Documentary | 7 | 5 | 12 |
| ai-tools | Software | 6 | 4 | 10 |
| windows-software | System | 6 | 4 | 10 |
| video-editing | Tutorial | 5 | 3 | 8 |
| english-learning | Education | 5 | 3 | 8 |
| taoist-classics | Text | 5 | 3 | 8 |
| android-tools | Software | 4 | 3 | 7 |
| discovery-science | Documentary | 3 | 2 | 5 |
| imax-doc | Documentary | 3 | 2 | 5 |
| space-universe | Documentary | 3 | 2 | 5 |
| war-history | Documentary | 3 | 1 | 4 |
| taoist-rituals | Text | — | 3 | 3 |
| ocean-wildlife | Documentary | — | 3 | 3 |
| natgeo-nature | Documentary | — | 2 | 2 |
| bbc-history | Documentary | — | 2 | 2 |
| taoist-manuscripts | Text | — | 2 | 2 |
| **Total** | | **50** | **50** | **100** |

### New Type Coverage

```
软件工具:  27 resources (AI tools + Windows + Android + Video editing)
纪录片:    32 resources (BBC + IMAX + Discovery + Space + Ocean + NatGeo)
经典文本:  16 resources (Taoist classics + rituals + manuscripts)
学习资源:   8 resources (English learning)
系统工具:  10 resources (Windows software)
历史:       7 resources (War + BBC history)
```

---

## 3. Reject Mechanism

### When to Reject

| Reason | Example | Action |
|--------|---------|--------|
| **Duplicate** | Resource is a lower-quality version of another in the same collection | REJECT — keep the better one |
| **No differentiation** | Standard software installer, identical to official download | REJECT — no editorial value to add |
| **Low quality** | Resource has missing files, broken links, or inaccurate description | REJECT — mark for cleanup, not editorial |
| **Too niche** | Single-file resource with no context needed | SKIP — editorial layer would be noise |
| **Outdated** | Resource superseded by a newer version in the same collection | REJECT — point to newer version |

### Implementation (no new schema fields)

Use existing `editorial_status` field:

```
editorial_status = 'rejected'
```

Add a `rejection_reason` as a comment in the audit log (existing `audit_log` table from migration 015):

```sql
INSERT INTO audit_log (entity_type, entity_id, action, detail)
VALUES ('resource', '<id>', 'editorial_rejected', '<reason>');
```

### Rejection Workflow

```
draft → [reviewer finds issue] → rejected (status updated, audit log entry)
                                   ↓
                            editorial_pilot.py --report excludes rejected
                            editorial_pilot.py --generate skips rejected
                            /admin/editorial-review.html hides rejected by default
```

---

## 4. Quality Metrics to Track

After 100-resource calibration:

| Metric | Target | Measurement |
|--------|--------|-------------|
| AI Guideline Check pass rate | >80% | editorial_pilot.py --report |
| EQS ≥ 20 (APPROVE on first review) | >50% | Human reviewer score |
| EQS ≥ 15 (APPROVE after minor edits) | >80% | Cumulative after REVISE |
| Reject rate | <10% | editorial_status = 'rejected' |
| Avg time per review | <2 min | Human reviewer clock |
| Forbidden phrase incidence | <2% | Guideline Check automated |
| Caveats presence rate | >95% | At least 1 caveat per resource |

---

## 5. Scale Decision

After 100-resource calibration, evaluate:

### GO conditions (all must be met):
- [ ] EQS ≥ 15 for >80% of reviewed resources
- [ ] Reject rate <10%
- [ ] Forbidden phrase rate <2%
- [ ] Reviewer can process >20 resources/hour
- [ ] At least 3 different resource types achieve EQS ≥ 20

### If GO:
```
Scale to all CORE + SOLID resources (~500 resources)
→ editorial_pilot.py --generate --tier CORE,SOLID
→ Batch review sessions (20/session)
→ Weekly calibration check (10 random samples)
```

### If NO-GO:
```
→ Revise AI prompt template
→ Add more forbidden phrases
→ Tighten Guideline Check rules
→ Re-run pilot with revised parameters
```

---

## 6. Reviewer Checklist

Before marking any resource as APPROVE:

```
[ ] 5-dimension EQS score assigned
[ ] Specificity ≥ 3 (contains concrete detail)
[ ] No forbidden phrases present
[ ] Audience is not "所有人/每个人"
[ ] At least 1 specific caveat
[ ] At least 2 differentiated strengths
[ ] Reads as human editorial judgment, not AI template
[ ] Would help a real user decide yes/no
```

---

> **Calibration framework ready. No schema changes. All quality tracking via existing fields + audit_log.**

# Phase 10.8.4 — Editorial Layer Implementation Plan

> Planning only. No code until confirmed.

---

## 1. Resource Detail — Final Page Structure

### Before

```
┌──────────────────────┐
│ TITLE                │  H1, centered
├──────────────────────┤
│ METADATA GRID        │  格式 | 大小 | 平台 | 版本
├──────────────────────┤
│ CTA                  │  [ 获取资源 ] button
├──────────────────────┤
│ "收录于 BigPRC..."   │  label
├──────────────────────┤
│ "链接失效？报告"       │  feedback
├──────────────────────┤
│ SEO DESCRIPTION      │  long AI text in desc-box
├──────────────────────┤
│ RELATED COLLECTIONS  │  pill links
├──────────────────────┤
│ RELATED RESOURCES    │  text links
├──────────────────────┤
│ "返回资源列表"        │  back link
└──────────────────────┘
```

### After

```
┌──────────────────────┐
│ TITLE                │  H1, centered
│ Resource Summary     │  1-line subtitle (NEW — always present)
├──────────────────────┤
│ EDITOR'S TAKE        │  Conditional: editorial_status == 'published'
│  ┌────────────────┐  │
│  │ 为什么推荐      │  │  editor_recommendation (1-3 sentences)
│  │                │  │
│  │ 适合            │  │  target_audience
│  │                │  │
│  │ 推荐理由        │  │  strengths (bullet list, + prefix)
│  │ + ...          │  │
│  │ + ...          │  │
│  │                │  │
│  │ 需要注意        │  │  caveats (bullet list, · prefix)
│  │ · ...          │  │
│  └────────────────┘  │
├──────────────────────┤
│ QUICK FACTS          │  格式 | 大小 | 平台 | 版本
│                       │  收录于 YYYY-MM (NEW)
│                       │  链接验证于 YYYY-MM (NEW)
├──────────────────────┤
│ CTA                  │  [ 获取资源 ] primary button
│                      │  [ 电脑端通道 ] secondary button
├──────────────────────┤
│ "收录于 BigPRC..."   │
│ 了解策展标准 →        │  (NEW — link to /curation)
├──────────────────────┤
│ SEO DESCRIPTION      │  long AI text (moved lower)
├──────────────────────┤
│ RELATED COLLECTIONS  │  pill links
│ RELATED RESOURCES    │  text links
├──────────────────────┤
│ 探索完整专题 →        │  (NEW — next step CTA)
│ 返回资源列表          │
└──────────────────────┘
```

### Module Purposes

| Position | Module | Purpose | For Whom |
|----------|--------|---------|----------|
| 1 | Title + Summary | Identify the resource | Everyone |
| 2 | **Editor's Take** | Help decide if this is right for you | New visitors |
| 3 | Quick Facts | Technical details | Returning users, power users |
| 4 | CTA | Take action | Users who decided to download |
| 5 | Trust signal | Build confidence in curation | Skeptical users |
| 6 | SEO Description | Search engine ranking | Googlebot |
| 7 | Related Content | Continue browsing | Users who want more |

### User Reading Order

```
Scan title → "Is this what I'm looking for?"
  ↓ YES
Read Editor's Take → "Is this the right version for me?"
  ↓ YES
Glance at Quick Facts → "Does the format/size work for me?"
  ↓ YES
Click CTA → Download
  ↓
See related collections → "What else is in this topic?"
  ↓
Continue browsing
```

### Desktop Layout

```
Max width: 680px, centered
Editor's Take: card-style panel (reuse .ed-panel from collection.html)
  background: var(--color-surface)
  border: var(--border-width) solid var(--color-border)
  border-radius: var(--radius-md)
  padding: var(--space-xl) var(--space-2xl)
Quick Facts: existing .info-grid (unchanged)
CTA: centered, existing button styles
```

### Mobile Layout (<768px)

```
Max width: 100vw - 32px padding
Editor's Take: same card, reduced padding (16px)
  strengths/caveats: full width
Quick Facts: 2×2 grid (existing mobile override)
CTA: full width button
```

---

## 2. Data Source Design

### Resource Summary (1-line subtitle)

| Aspect | Detail |
|--------|--------|
| **Source** | Existing AI-generated `tagline` field (from `ai_seo_writer.py`) |
| **Generation** | Already exists in DB for most resources |
| **Coverage** | Partial — resources processed by `ai_seo_writer.py` have it |
| **Fallback** | If NULL, omit the subtitle line entirely |
| **Display** | 14px, secondary color, centered, max 80 chars |

### Editor's Take (4 fields)

| Aspect | Detail |
|--------|--------|
| **Source** | `collection_editor_ai.py` (NEW generation mode for resources) |
| **Required for** | Spotlight resources + resources in CORE/SOLID collections |
| **Optional for** | NICHE resources; all others |
| **Skip rule** | If resource has no meaningful differentiation, leave all fields NULL |
| **Guard** | `{% if editorial_status == 'published' %}` — only show approved content |

### SEO Description

| Aspect | Detail |
|--------|--------|
| **Source** | Existing `seo_desc` field (from `ai_seo_writer.py`) |
| **Change** | No change to generation logic |
| **Position** | Moves below CTA (was above related content, now between trust signal and related) |

---

## 3. Database Implementation

### ALTER TABLE — Add 8 Columns

```sql
-- Core editorial fields
ALTER TABLE resources ADD COLUMN editor_recommendation TEXT;
ALTER TABLE resources ADD COLUMN target_audience TEXT;
ALTER TABLE resources ADD COLUMN strengths TEXT;          -- JSON array, e.g. '["...","..."]'
ALTER TABLE resources ADD COLUMN caveats TEXT;             -- JSON array

-- Workflow metadata
ALTER TABLE resources ADD COLUMN editorial_status TEXT DEFAULT NULL;
ALTER TABLE resources ADD COLUMN reviewed_at TEXT DEFAULT NULL;
ALTER TABLE resources ADD COLUMN generated_at TEXT DEFAULT NULL;
ALTER TABLE resources ADD COLUMN ai_model TEXT DEFAULT NULL;

-- Existing fields leveraged
-- tagline      → Resource Summary (already exists)
-- seo_desc     → SEO Description (already exists)
-- created_at   → "收录于" date in Quick Facts
-- last_checked → "链接验证于" date in Quick Facts (if exists)
```

### NULL Strategy

| Field | NULL means | When NULL |
|-------|-----------|-----------|
| `editor_recommendation` | No editorial content yet | AI not run, or resource skipped |
| `target_audience` | Same | Same |
| `strengths` | Same | Same |
| `caveats` | Same | Same |
| `editorial_status` | Not in editorial workflow | Resource not yet processed |
| `reviewed_at` | Not reviewed yet | Draft or not processed |
| `generated_at` | Not AI-generated yet | Not processed |
| `ai_model` | Not AI-generated | Not processed |

### Backward Compatibility

All new columns are `DEFAULT NULL`. Existing queries and rendering continue to work unchanged. The `{% if editorial_status == 'published' %}` guard ensures editorial UI only appears when content is ready.

### Migration Script

```sql
-- Run once, idempotent (SQLite ignores IF NOT EXISTS for columns in some versions)
-- Safe to run multiple times — will not error on existing columns in SQLite 3.35+
```

---

## 4. AI Generation Pipeline

### Resource Selection

```
Priority 1: Spotlight resources (already editor-approved at collection level)
Priority 2: CORE collection resources (flagship content)
Priority 3: SOLID collection resources (strong content)
Skip:      NICHE + EMPTY (low priority, or no differentiation)
```

### Prompt Design

```
System:
你是 BigPRC 的数字资源策展编辑。
你的任务是帮助用户判断一个资源是否适合他们。

Rules:
1. 每句话必须包含具体信息 (版本号、时间范围、文件特征)
2. 不使用 "非常优秀" "功能强大" "强烈推荐" "值得推荐"
3. target_audience 不能写 "所有人"
4. caveats 必须真实 — 如果找不到限制，说明你不够了解这个资源
5. 总字数控制在 150 字以内

User:
资源名称: {title}
资源类型: {category}
文件大小: {size}
平台: {platform}
版本: {version}
所属专题: {collection_title}
现有描述: {seo_desc}

请输出 JSON:
{
  "editor_recommendation": "...",
  "target_audience": "...",
  "strengths": ["...", "...", "..."],
  "caveats": ["...", "..."]
}
```

### Anti-AI-Generic Methods

| Problem | Solution |
|---------|----------|
| "非常适合初学者" | Require specificity: "适合从未接触过 XX 的用户" |
| "功能全面" | Forbidden phrase — regex filter in Guideline Check |
| strengths all sound the same | Prompt includes example of good variety |
| caveats always empty | Prompt requires at least 1 caveat; empty = FAIL |
| template-like structure | Vary sentence starters — don't always begin with "这是" |

### Quality Gate (Automated)

```python
def guideline_check(editorial: dict) -> bool:
    """Run before editor review. Returns True if passes."""
    forbidden = ["非常优秀", "功能强大", "强烈推荐", "值得推荐", "所有人"]
    text = editorial["editor_recommendation"] + editorial["target_audience"]

    for phrase in forbidden:
        if phrase in text:
            return False  # FAIL: generic praise

    if len(editorial["strengths"]) == 0:
        return False  # FAIL: no strengths

    if len(editorial["caveats"]) == 0:
        return False  # FAIL: no caveats (every resource has limits)

    if len(editorial["editor_recommendation"]) < 30:
        return False  # FAIL: too short to be useful

    return True
```

### Human Review Checklist

```
[ ] Version numbers / dates mentioned are accurate
[ ] Audience description matches actual content difficulty
[ ] Strengths are verifiable (not just opinion)
[ ] Caveats are honest and specific
[ ] Reads like a human editor, not an AI template
[ ] Would help a real user decide yes/no
```

---

## 5. Visual Specification

### Allowed (reuse existing Design System)

```
Typography:  --text-body (14px) for recommendation/audience
             --text-meta (12px) for strengths/caveats labels
             --text-caption (11px) for trust signal line

Color:       --color-text for recommendation
             --color-text-secondary for audience/caveats
             --color-accent for "+" strength markers

Spacing:     --space-xl (20px) panel padding
             --space-md (12px) between sections
             --space-sm (8px) between items

Component:   .ed-panel (reuse from collection.html)
             .info-grid (existing, unchanged)
             .btn--primary / .btn--secondary (existing)

Icon:        pencil-line (编辑推荐) — Lucide, flat, muted
```

### Forbidden

```
❌ New colors
❌ New font sizes
❌ New component variants
❌ Emoji as UI elements
❌ 3D / gradient / decorative icons
❌ Box shadows on editorial panel
```

### Icon Rule (reconfirmed)

```
All future icons: Lucide, flat, linear, monochrome.
Icon purpose: aid information recognition — never the visual focus.
Emoji banned as UI elements permanently.
```

---

## 6. Pilot Scope — 50 Resources

### Selection

| Tier | Count | Rationale |
|------|-------|-----------|
| Spotlight resources | 10 | Highest visibility, already editor-approved at collection level |
| BBC Nature collection | 8 | Flagship collection, highest traffic |
| AI Tools collection | 6 | High SEO value |
| Windows Software collection | 6 | Practical utility, high download volume |
| Video Editing collection | 5 | Professional audience, values editorial guidance |
| English Learning collection | 5 | Large audience, needs clear level differentiation |
| Taoist Classics collection | 5 | Niche academic audience, benefits most from editorial context |
| Other collections | 5 | Diversity coverage |

### Success Metrics (to evaluate after pilot)

| Metric | Target |
|--------|--------|
| Editor's Take presence on pilot pages | 50/50 |
| Average time on page change | Monitor (expect increase for editorial pages) |
| Bounce rate change | Monitor (expect decrease) |
| Download CTR change | Monitor (expect slight increase from informed users) |
| Guideline Check pass rate (AI output) | >80% on first generation |
| Human review approval rate | >70% (some AI rejection expected) |

### Go/No-Go Decision

After 50-resource pilot:
- **Go**: Editorial voice is consistent, content quality meets Guideline, user metrics trending positive → scale to all CORE + SOLID resources.
- **No-Go**: Content reads as AI-generated despite Guideline, or user metrics show no improvement → revise prompt/Guideline before scaling.

---

> **Implementation plan complete. Awaiting confirmation to begin Phase 1 (Schema Migration).**

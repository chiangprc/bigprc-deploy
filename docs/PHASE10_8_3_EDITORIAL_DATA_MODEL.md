# Phase 10.8.3 — Editorial Content Data Model

> Design only. No code. Every field must answer: "Does this help the user decide?"

---

## 1. Resource Editorial Fields

### Core Fields (v1.0)

| Field | Type | Required | Max | Purpose |
|-------|------|----------|-----|---------|
| `editor_recommendation` | TEXT | ✅ | 200 chars | "Why is this worth my time?" |
| `target_audience` | TEXT | ✅ | 100 chars | "Is this for someone like me?" |
| `strengths` | TEXT (JSON array) | ✅ | 3 items, 40 chars each | "What makes this the best choice?" |
| `caveats` | TEXT (JSON array) | — | 3 items, 40 chars each | "What should I know before downloading?" |

### Why these four, nothing else

| Field | User Question Answered | Without It |
|-------|----------------------|------------|
| `editor_recommendation` | "Why should I care?" | User skips to download link — no editorial value |
| `target_audience` | "Is this for me?" | User downloads, discovers it's not for them → frustration |
| `strengths` | "Is it actually good?" | User has no way to compare with alternatives |
| `caveats` | "What's the catch?" | User discovers limitations after download → broken trust |

### What we deliberately excluded

| Proposed Field | Why Excluded |
|---------------|-------------|
| `use_cases` (list) | Overlaps with `target_audience`. Audience implies use case. |
| `alternatives` (list) | Better handled by "Related Resources" section, not editorial text. |
| `rating` (score) | Numerical ratings invite comparison across categories — meaningless for curation. |
| `editor_name` | "BigPRC 编辑" is sufficient. Individual attribution adds complexity without user value. |
| `last_updated` (resource) | Separate concern — belongs in Quick Facts, not Editor's Take. |
| `difficulty_level` | Covered by `target_audience` ("初学者" implies beginner). |

### `strengths` and `caveats` as JSON arrays

SQLite has no native array type. Store as JSON text:

```json
["覆盖完整流程，不需要另外找教程", "每个案例都有源文件", "中文字幕为人工翻译"]
```

This allows:
- Rendering as bullet list in HTML
- AI generation as structured output
- Editor review as individual items (approve/reject per strength)

---

## 2. Editorial Workflow Status

### Status Enum

```
draft       → AI generated, not yet reviewed by human
reviewed    → Human editor has checked and approved content
published   → Live on site, visible to users
rejected    → Editor determined content is unsuitable, back to draft
```

### Status Transitions

```
                    ┌─────────┐
                    │  draft  │  ← AI generates initial content
                    └────┬────┘
                         │
                    editor reviews
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌──────────┐
         │published│ │reviewed│ │ rejected │
         └────────┘ └───┬────┘ └────┬─────┘
                         │           │
                    editor approves  │
                         │           │
                         ▼           ▼
                    ┌────────┐  ┌────────┐
                    │published│  │ draft  │ ← regenerate
                    └────────┘  └────────┘
```

### Why `reviewed` and `published` are separate

`reviewed` = content is accurate, but the editor hasn't decided to show it publicly yet (e.g., waiting for collection launch).

`published` = live on the site.

This allows batching — review 50 resources, then publish them together when the collection goes live.

### Metadata Fields

| Field | Type | Purpose |
|-------|------|---------|
| `editorial_status` | TEXT | Current workflow state |
| `reviewed_at` | TEXT (ISO datetime) | When last reviewed |
| `generated_at` | TEXT (ISO datetime) | When AI generated the draft |
| `ai_model` | TEXT | Which model generated the draft (for quality tracking) |

No `reviewed_by` — single-editor operation for now. Add if team grows.

---

## 3. Three-Way Content Distinction

### The Problem

BigPRC will have three pieces of text about each resource. If they overlap, users will skim past all of them. If they serve different purposes, each one adds value.

### The Distinction

```
┌─────────────────────────────────────────────────────────────┐
│ RESOURCE TITLE                                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  RESOURCE SUMMARY (1 line)                                    │
│  "What is this?"                                              │
│  AI-generated. Always present.                               │
│  Appears directly below title.                                │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  EDITOR'S TAKE (4 fields, ~65 words)                          │
│  "Why should I care? Is this for me?"                        │
│  AI draft → editor reviewed. May be absent.                  │
│  If absent: skip to Quick Facts.                              │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  QUICK FACTS                                                  │
│  Format · Size · Platform · Version                           │
│  Always present. Machine data.                                │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  SEO DESCRIPTION (80-200 words)                               │
│  "What does Google need to know?"                             │
│  AI-generated. Always present.                               │
│  Positioned below CTA — users scroll past, Google reads it.  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Conflict Prevention

| Scenario | Rule |
|----------|------|
| Editor's Take repeats SEO description | Regenerate Editor's Take — it's not doing its job |
| SEO description contains judgment ("最好的") | Strip evaluative language from SEO text |
| Resource Summary is too long | Cap at 60 chars. It's a label, not a description. |

---

## 4. AI-Assisted Generation Pipeline

### Flow

```
Resource Data (title, category, seo_desc, collection context)
        │
        ▼
┌──────────────────┐
│ AI Draft         │  ← collection_editor_ai.py
│ - recommendation │     Prompt: Editorial Guideline §7 template
│ - audience       │     Output: structured JSON
│ - strengths[]    │
│ - caveats[]      │
│ status: draft    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Guideline Check  │  ← automated
│ - No "非常优秀"   │     Regex for forbidden phrases
│ - No "所有人"     │     Regex for generic audience
│ - Strengths ≤ 3  │     Count validation
│ - Caveats ≤ 3    │     Count validation
│ - Each field ≤   │     Length validation
│   char limit     │
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
  PASS      FAIL → regenerate with stricter prompt
    │
    ▼
┌──────────────────┐
│ Editor Review    │  ← manual
│ - Accuracy check │     Is version info correct?
│ - Tone check     │     Does it sound like BigPRC?
│ - Caveats real?  │     Are limitations honest?
│ status: reviewed │
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
  APPROVE   REJECT → back to draft
    │
    ▼
┌──────────────────┐
│ Publish          │
│ status: published │
└──────────────────┘
```

### Quality Gates

| Gate | Automated? | Checks |
|------|-----------|--------|
| Forbidden phrases | ✅ | "非常优秀", "功能强大", "强烈推荐", "值得推荐", "所有人" |
| Length limits | ✅ | recommendation ≤ 200, audience ≤ 100, strengths ≤ 3, caveats ≤ 3 |
| Content uniqueness | ✅ | Editor's Take ≠ SEO description (cosine similarity check) |
| Accuracy | ❌ | Human review — version numbers, dates, factual claims |
| Tone | ❌ | Human review — reads as editorial, not AI |
| Caveat honesty | ❌ | Human review — are limitations actually mentioned? |

---

## 5. Database Schema

### Option A: Extend Existing Table (Recommended)

If resources live in a `resources` table, add columns:

```sql
ALTER TABLE resources ADD COLUMN editor_recommendation TEXT;
ALTER TABLE resources ADD COLUMN target_audience TEXT;
ALTER TABLE resources ADD COLUMN strengths TEXT;          -- JSON array
ALTER TABLE resources ADD COLUMN caveats TEXT;             -- JSON array
ALTER TABLE resources ADD COLUMN editorial_status TEXT DEFAULT 'draft';
ALTER TABLE resources ADD COLUMN reviewed_at TEXT;
ALTER TABLE resources ADD COLUMN generated_at TEXT;
ALTER TABLE resources ADD COLUMN ai_model TEXT;
```

Pros: No JOIN needed. Simple query. Existing `detail.html` template already has access to the resource row.

### Option B: Separate Table

```sql
CREATE TABLE resource_editorial (
    resource_id TEXT PRIMARY KEY,
    editor_recommendation TEXT,
    target_audience TEXT,
    strengths TEXT,           -- JSON array
    caveats TEXT,             -- JSON array
    editorial_status TEXT DEFAULT 'draft',
    reviewed_at TEXT,
    generated_at TEXT,
    ai_model TEXT,
    FOREIGN KEY (resource_id) REFERENCES resources(id)
);
```

Pros: Clean separation. Doesn't bloat the main resources table.
Cons: JOIN required in template rendering.

### Recommendation: Option A

BigPRC is a single-developer project. The simplicity of avoiding JOINs outweighs the theoretical cleanliness of a separate table. The eight new columns are all TEXT and will be NULL for resources without editorial content — no performance impact on SQLite.

---

## 6. Template Rendering Logic

```jinja2
{% if editorial_status == 'published' %}
<!-- Editor's Take Section -->
<div class="ed-panel">
    <h3 class="ed-panel-title">
        <i data-lucide="pencil-line" class="icon-sm icon-muted"></i> 编辑推荐
    </h3>
    <p class="ed-recommendation">{{ editor_recommendation }}</p>
    <p class="ed-audience"><strong>适合</strong>：{{ target_audience }}</p>
    {% if strengths %}
    <ul class="ed-strengths">
    {% for s in strengths|fromjson %}
        <li>+ {{ s }}</li>
    {% endfor %}
    </ul>
    {% endif %}
    {% if caveats %}
    <div class="ed-caveats">
        <strong>需要注意</strong>：
        {% for c in caveats|fromjson %}
        <span>· {{ c }}</span>
        {% endfor %}
    </div>
    {% endif %}
</div>
{% endif %}
```

The `{% if editorial_status == 'published' %}` guard means:
- Resources without editorial content: no empty boxes
- Resources with content still in review: not visible
- Published editorial content: rendered with full structure

---

## 7. Migration Path

### Phase 1: Schema Only
- Add columns to resources table
- All new columns DEFAULT NULL (backward compatible)
- Existing pages render unchanged (editorial_status is NULL → condition fails)

### Phase 2: AI Generation
- Run `collection_editor_ai.py` on 50 pilot resources
- Output: editorial_status = 'draft'
- Not visible to users yet

### Phase 3: Editor Review
- Manual review of 50 drafts
- Approve → status = 'published'
- Visible on site for the first time

### Phase 4: Scale
- Expand AI generation to all CORE + SOLID resources
- Batch review workflow
- Monitor quality with Guideline Check automated gate

---

> **Data model frozen. 4 editorial fields, 4 workflow states, 3-way content distinction. No over-engineering.**

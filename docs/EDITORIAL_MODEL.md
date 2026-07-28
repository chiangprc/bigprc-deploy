# BigPRC Editorial Model — Phase 9 Design

> **Status**: Design Phase  
> **Depends on**: Rule Engine v0.8 (Frozen)  

---

## 1. Editorial Field Definitions

### `editor_note` — Editor's Recommendation

| Property | Value |
|----------|-------|
| **定位** | 编辑推荐语。表达编辑对这个专题的策展判断 |
| **回答** | "为什么值得收藏？这个专题的独特价值是什么？" |
| **建议长度** | 100-200 字 |
| **来源** | AI 可生成初稿（`collection_editor_ai.py` prompt 已覆盖），最终人工审核 |
| **是否需要人工确认** | **是。必须。** 这是策展判断的核心表达 |
| **前端展示** | 专题页 Hero 下方，`{% if editor_note %}` 区块 |
| **是否允许 AI 自动发布** | 否。AI draft → editor review → publish |

**Good example**:
```
BBC 自然纪录片不是简单的动物影像记录，而是人类理解地球生态系统的一套视觉百科。
从《蓝色星球》的深海探索到《绿色星球》的植物视角，这些作品以科学严谨性和影像美学并重，
既是自然科普的权威参考，也是家庭收藏的视听精品。
```

**Bad example**:
```
这是非常优秀的纪录片合集，值得收藏。  ← 空洞无物
```

---

### `why_collect` — Why This Collection Exists

| Property | Value |
|----------|-------|
| **定位** | 收藏理由。一句话说明建立这个专题的策展动机 |
| **回答** | "为什么 BigPRC 要建立这个专题？" |
| **建议长度** | 一句话（≤50 字） |
| **来源** | 编辑撰写。AI 可基于 resource 数据提供 draft |
| **是否需要人工确认** | 是 |
| **前端展示** | 专题页 "为什么值得收藏" 卡片 |
| **是否允许 AI 自动生成** | 可生成 draft，人工确认 |

**Example**:
```
精选 BBC 自然纪录片经典系列，为自然爱好者提供高质量的影像资料库。
```

---

### `audience` — Target Audience

| Property | Value |
|----------|-------|
| **定位** | 适合人群。帮助用户判断"这个专题对我有用吗" |
| **回答** | "这个专题适合谁？" |
| **格式** | 分号分隔的短标签列表。如："自然爱好者；纪录片收藏者；儿童科普启蒙家长；中学地理/生物教师" |
| **来源** | AI 初稿 + 编辑审核 |
| **是否需要人工确认** | 是 |
| **前端展示** | 专题页 "适合人群" 卡片 |
| **是否允许 AI 自动生成** | 可生成 draft，人工确认 |

---

### `highlights` — Collection Highlights

| Property | Value |
|----------|-------|
| **定位** | 精选亮点。突出专题中最值得关注的资源或特点 |
| **回答** | "这个专题里有什么特别值得看的？" |
| **格式** | JSON 数组，每条 15-30 字。3-5 条 |
| **来源** | AI 初稿（基于资源标题 + SEO 描述）+ 编辑审核 |
| **是否需要人工确认** | 是 |
| **前端展示** | 专题页 "精选亮点" 列表 (`<ul>`) |
| **是否允许 AI 自动生成** | 可生成 draft，人工确认 |

**Example**:
```json
[
  "《蓝色星球》系列：海洋纪录片的标杆之作",
  "《地球脉动》：跨越全球的生态奇观",
  "《绿色星球》：以植物视角重新理解自然",
  "中文字幕 + 高清画质，适合全年龄段观看"
]
```

---

## 2. AI Generation Policy

| Field | AI Can Draft | AI Can Publish | Human Required |
|-------|-------------|---------------|----------------|
| `intro` | ✅ | ✅ (pre-generated, editor can regenerate) | Review only |
| `seo_title` | ✅ | ✅ | Review only |
| `seo_desc` | ✅ | ✅ | Review only |
| `faq_json` | ✅ | ✅ | Review only |
| `editor_note` | ✅ | ❌ | **Required** |
| `why_collect` | ✅ | ❌ | **Required** |
| `audience` | ✅ | ❌ | **Required** |
| `highlights` | ✅ | ❌ | **Required** |

**Principle**: AI writes drafts for everything. SEO/info content can be published after batch review. Editorial content requires explicit per-field human approval. This reflects the reality that a wrong FAQ answer is fixable, but a wrong editorial voice damages the platform's credibility.

---

## 3. Editorial Generation Pipeline (Redesigned)

### Current `collection_editor_ai.py`

Generates: `intro`, `seo_title`, `seo_desc` only.  
Does NOT generate: `editor_note`, `why_collect`, `audience`, `highlights`.

### Phase 9.1 Redesign

**One script, two output modes**:

```
Mode A: Content (auto-publish)
  python3 collection_editor_ai.py --content
  → intro, seo_title, seo_desc, faq_json
  → writes to collection_content
  → no manual review needed (batch audit)

Mode B: Editorial (draft only)
  python3 collection_editor_ai.py --editorial
  → editor_note, why_collect, audience, highlights
  → writes to collection_content but marks as draft
  → requires editor review before frontend display
```

**Prompt Design**:

Mode B prompt:
```
You are an editorial curator for BigPRC, a curated digital resource library.
Based on the collection title, description, and sample resources,
generate four editorial content pieces:

1. editor_note (100-200 chars): Curatorial perspective. Why is this collection worth collecting?
2. why_collect (one sentence): Why does this collection exist?
3. audience (semicolon-separated list): Who will benefit from this collection?
4. highlights (JSON array of 3-5 strings, 15-30 chars each): What are the standout resources or features?

Rules:
- Be specific. Reference actual resource names from the samples.
- Be honest. Don't over-promise.
- Be useful. Help the user decide "is this for me?"

Output JSON:
{"editor_note":"...","why_collect":"...","audience":"...","highlights":["...","..."]}
```

---

## 4. Phase 9 Roadmap

### Phase 9.1 — Editorial Generation Pipeline
```
Deliverable: Updated collection_editor_ai.py with --editorial mode
Status: Design complete, ready for implementation
Dependencies: None (reads existing collections + resource data)
Schema change: None (writes to existing collection_content columns)
```

### Phase 9.2 — Editorial Dashboard
```
Deliverable: /admin/editorial.html
Purpose: Shows editorial completeness for all 16 collections
Data: editorial.json (new export)
Schema change: None
```

### Phase 9.3 — Editorial Editor
```
Deliverable: /admin/editorial-edit.html?id=
Purpose: Text areas for writing editorial content + preview
Data: editorial.json (read) + CLI for write
Schema change: None
```

### Phase 9.4 — Frontend Integration
```
Deliverable: None (templates already have {% if %} blocks)
Purpose: Editorial content automatically appears on frontend once populated
Schema change: None
```

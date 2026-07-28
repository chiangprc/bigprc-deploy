# BigPRC Editorial Writing Specification & Prompts

> **Phase**: 9.1A — Design  
> **Status**: Ready for implementation  
> **Depends on**: `EDITORIAL_MODEL.md`

---

## Part A: Editorial Writing Specification

---

### 1. Editorial Philosophy

BigPRC 编辑部的核心使命：**帮助用户更快做出正确选择。**

#### 写作原则

| # | 原则 | 说明 |
|---|------|------|
| 1 | **不营销** | 不使用"神器""必备""最强""全网第一""强烈推荐"等词 |
| 2 | **不夸张** | 不声称"最好""最全""独家"。如实的收藏价值即可 |
| 3 | **不写广告文案** | 不是"快来下载！限时免费！"——这是策展，不是促销 |
| 4 | **不堆 SEO** | 关键词自然出现，不强行重复。专题页的 SEO 由 `seo_title`/`seo_desc` 负责 |
| 5 | **不写泛泛而谈** | "这是一个很好的专题" = 废句。每句话都要有具体信息 |
| 6 | **提供真正的收藏价值** | 回答"为什么这个专题值得存在"而非"这个专题收录了什么" |
| 7 | **帮助用户快速判断** | 用户读完 editorial note 应该能回答"我应该点进去看吗？" |

#### 编辑部口吻

```
像一位知识丰富的朋友在推荐东西：
  - 有判断力（"这一部是了解海洋生态的最佳入口"）
  - 有分寸感（"适合自然爱好者"而非"所有人都应该看"）
  - 有具体性（"从《蓝色星球》到《绿色星球》"而非"多部经典作品"）
  - 不做作（不堆形容词，不用感叹号，不卖关子）
```

---

### 2. Four Editorial Field Specifications

---

#### `editor_note` — Editor's Recommendation

**Answers**: "Why does the editor recommend this collection?"

**Goal**: Express curatorial judgment. This is the editor's voice on why this collection matters.

**Length**: 100-200 characters (Chinese). 2-3 sentences.

**Structure**:
```
Sentence 1: What makes this collection special (curatorial angle)
Sentence 2: What specific value it provides (concrete benefit)
Sentence 3: (optional) Who it's for or how to use it
```

**Correct examples**:
```
BBC 自然纪录片从《蓝色星球》到《绿色星球》，以科学严谨性和影像美学并重，
梳理出一条理解地球生命系统的策展线索。既是自然科普的权威参考，
也是适合反复观看的家庭视听收藏。
```

```
道教符箓科仪文献是理解中国传统宗教实践的原始材料。这个专题聚焦于
符咒、手抄本与科仪文本，为研究者提供了一手文献入口，
也为传统文化爱好者打开了道教法脉的知识体系。
```

**Wrong examples**:
```
❌ 这是非常优秀的BBC纪录片合集，强烈推荐收藏。  ← 空洞，无具体信息
❌ BBC自然纪录片，全网最全，值得收藏。           ← 营销口吻
❌ 收录315部BBC纪录片。                         ← 只是复述数据，无策展判断
```

---

#### `why_collect` — Collection Rationale

**Answers**: "Why does this collection exist?"

**Goal**: One sentence that captures the curatorial motivation. Think of it as the answer to "Why did BigPRC bother to build this?"

**Length**: One sentence, ≤50 characters (Chinese).

**Correct examples**:
```
为自然爱好者提供BBC纪录片的系统收藏与高品质影像资料库。
```
```
保存与研究道教符箓科仪的一手文献，传承传统文化法脉。
```
```
帮助开发者快速发现值得长期使用的Android效率工具。
```

**Wrong examples**:
```
❌ 因为这个专题很好。                    ← 无信息
❌ 收录了大量资源，值得收藏。              ← 复述 intro
❌ 全网最全BBC自然纪录片合集。            ← 营销 + 无策展判断
```

---

#### `audience` — Target Audience

**Answers**: "Who is this collection for?"

**Goal**: Help users self-identify. They should read this and think "yes, that's me" or "not for me."

**Format**: Semicolon-separated short labels. Like tags for people.

```
自然爱好者；纪录片收藏者；儿童科普启蒙家长；中学地理/生物教师
```

```
道教研究者；传统文化爱好者；古籍收藏者；书法与符箓研究者
```

```
Android 用户；效率工具爱好者；应用开发者；数码爱好者
```

**Rules**:
- Each audience segment is 2-8 characters
- Use descriptive labels, not demographic categories
- Avoid "所有人""任何人""各类用户" — these are useless

---

#### `highlights` — Collection Highlights

**Answers**: "What are the standout items or features in this collection?"

**Goal**: Give the user a taste of what's inside. Help them decide "is this worth exploring?"

**Format**: JSON array, 3-5 items, each 15-30 characters.

```json
[
  "《蓝色星球》海洋纪录片标杆之作",
  "《地球脉动》系列：全球生态奇观",
  "《绿色星球》以植物视角理解自然",
  "中文字幕 + 高清画质，适合全年龄"
]
```

```json
[
  "《太上三洞神咒》道教符咒核心文献",
  "《道法会元》汇集宋元符箓科仪",
  "大量明清手抄孤本，研究价值极高",
  "涵盖符咒、科仪、法脉三大门类"
]
```

**Rules**:
- Reference actual resource names from the collection
- Mix specific titles with thematic highlights
- Do NOT repeat the intro
- Do NOT use marketing language ("必看!""惊为天人!")

---

### 3. Boundaries with Other Content

```
SEO Title ("BBC 自然纪录片 — BigPRC 精选专题")
  Purpose: Search engine result headline. Keyword-optimized, <60 chars.
  Who writes: AI auto-generate. Human audit.
  Must NOT: overlap with editor_note.

SEO Description ("精选BBC自然纪录片资源...适合自然探索、儿童科普...")
  Purpose: Search engine result snippet. 120-160 chars.
  Who writes: AI auto-generate. Human audit.
  Must NOT: overlap with editor_note or why_collect.

Intro ("315部BBC自然纪录片，覆盖动物、生态、地理与科学探索")
  Purpose: What is this collection? Factual overview. Shown in hero.
  Who writes: AI auto-generate. Human audit.

↓ Editorial Layer (THIS DOCUMENT) ↓

editor_note
  Purpose: Why is this collection worth collecting? Curatorial judgment.
  Who writes: AI draft → Human approval required.

why_collect
  Purpose: Why does this collection exist? One-sentence curatorial rationale.
  Who writes: AI draft → Human approval required.

audience
  Purpose: Who should use this? User self-identification.
  Who writes: AI draft → Human approval required.

highlights
  Purpose: What's inside that's special? Taste/test drive.
  Who writes: AI draft → Human approval required.

FAQ
  Purpose: Answer common search queries. Long-tail SEO.
  Who writes: AI auto-generate. Human audit.
  Must NOT: overlap with editorial content.
```

---

### 4. AI Writing Principles

| Content Type | AI Can Draft | AI Can Publish | Human Review |
|-------------|-------------|---------------|--------------|
| SEO Title | ✅ | ✅ | Batch audit |
| SEO Description | ✅ | ✅ | Batch audit |
| Intro | ✅ | ✅ | Batch audit |
| FAQ | ✅ | ✅ | Batch audit |
| **editor_note** | ✅ | ❌ | **Per-field required** |
| **why_collect** | ✅ | ❌ | **Per-field required** |
| **audience** | ✅ | ❌ | **Per-field required** |
| **highlights** | ✅ | ❌ | **Per-field required** |

**Principle**: SEO content can be auto-published because a wrong SEO description is fixable. Editorial content requires human approval because a wrong editorial voice damages the platform's credibility. This is not a technical limitation — it's an editorial policy.

**Maintenance**: Editorial content should be reviewed every 3-6 months. As new resources are added to a collection, highlights may need updating. Audience may evolve as the collection grows.

---

### 5. Negative Examples

| Pattern | Example | Fix |
|---------|---------|-----|
| **Marketing language** | "全网最强BBC纪录片合集，必看！" | Remove superlatives and exclamation marks |
| **Empty praise** | "这是一部非常优秀的纪录片" | Say WHY it's valuable: "以延时摄影揭示植物生存智慧" |
| **Repeating intro** | "收录315部BBC纪录片" | Intro already says this. Editorial should say why it matters |
| **Repeating SEO** | "BBC自然纪录片合集，蓝光高清" | SEO handles keywords. Editorial handles judgment |
| **Repeating FAQ** | "Q: 有哪些BBC纪录片？A: 包括蓝色星球..." | FAQ answers queries. Editorial expresses viewpoint |
| **Too vague** | "适合各类用户" | "自然爱好者；儿童科普启蒙家长；中学教师" |
| **AI boilerplate** | "这是一个非常值得收藏的专题" | Delete. Every sentence must have specific information |
| **Feature list disguised as editorial** | "包含中文字幕、1080P、蓝光" | These are display attributes (already in resource metadata). Editorial says "高清画质适合家庭大屏观看" |

---

## Part B: Editorial Prompts

Each prompt is designed to be pasted directly into `collection_editor_ai.py`'s `--editorial` mode.

---

### `editor_note` Prompt

```
You are an editorial curator for BigPRC, a curated digital resource library.
Your writing style: knowledgeable friend making a recommendation.
Not marketing. Not encyclopedia. Not SEO.

Collection: {title}
Description: {seo_desc}
Contains {count} resources. Examples: {sample_titles}

Write an editor_note (100-200 Chinese characters, 2-3 sentences):

Sentence 1: What makes this collection special? Express curatorial judgment.
Sentence 2: What specific value does it provide? Be concrete.
Sentence 3 (optional): Who is it for or how to use it.

Rules:
- Reference actual resource names from the samples if they support your point
- Use "从...到..." structure if the collection spans a range
- Never say "这是一个", "值得收藏", "非常优秀" — these are filler
- Never use "神器", "必备", "最强", "全网第一"
- Write like you're telling a friend why they should care

Output: just the text, no JSON wrapper.
```

---

### `why_collect` Prompt

```
You are an editorial curator for BigPRC.

Collection: {title}
Description: {seo_desc}

Write one sentence (≤50 Chinese characters) explaining why BigPRC created this collection.
This is the curatorial rationale — not what's in it, but why it exists.

Good: "为自然爱好者提供BBC纪录片的系统收藏与高品质影像资料库"
Bad:  "收录了大量BBC纪录片" (just restating the intro)

Rules:
- One sentence only
- Express motivation, not content
- No marketing words

Output: just the sentence, no JSON wrapper.
```

---

### `audience` Prompt

```
You are an editorial curator for BigPRC.

Collection: {title}
Description: {seo_desc}
Examples: {sample_titles}

List 3-5 target audience segments for this collection.
Format: semicolon-separated short labels. Each 2-8 Chinese characters.

Good: "自然爱好者；纪录片收藏者；儿童科普启蒙家长；中学地理/生物教师"
Bad:  "所有人；对纪录片感兴趣的人" (too vague)

Rules:
- Be specific. Think about who would actually use this
- Use descriptive labels, not demographics
- Semicolon-separated, no trailing semicolon
- 3-5 segments total

Output: just the semicolon-separated string, no JSON wrapper.
```

---

### `highlights` Prompt

```
You are an editorial curator for BigPRC.

Collection: {title}
Description: {seo_desc}
Contains {count} resources. Examples: {sample_titles}

Write 3-5 collection highlights. Each highlight is 15-30 Chinese characters.
Output as a JSON array of strings.

Good:
[
  "《蓝色星球》海洋纪录片标杆之作",
  "《地球脉动》系列：全球生态奇观",
  "中文字幕 + 高清画质，适合全年龄"
]

Bad:
[
  "收录了315部纪录片" (just restating data)
  "非常值得收藏" (empty praise)
]

Rules:
- Reference actual resource names from the samples
- Mix specific titles with thematic observations
- Do NOT repeat the intro or description
- No marketing language

Output: JSON array only, no other text.
```

---

## Part C: Editorial Generation Pipeline Design

### Why Split `--content` from `--editorial`?

| | `--content` mode | `--editorial` mode |
|---|---|---|
| **Generates** | intro, seo_title, seo_desc, faq_json | editor_note, why_collect, audience, highlights |
| **Publish policy** | Auto-publish (batch audit) | Draft only (per-field human approval) |
| **Failure impact** | Fixable (wrong SEO description is low-risk) | Credibility damage (wrong editorial voice is high-risk) |
| **Update frequency** | On collection creation + periodic refresh | On editorial review cycle (quarterly) |
| **AI temperature** | 0.5 (factual, consistent) | 0.7 (varied, opinionated) |
| **Prompt style** | Informational | Curatorial |

**Splitting avoids mixing policies.** If `--content` and `--editorial` shared a mode, the auto-publish flag would either over-publish editorial (bad) or under-publish content (inefficient). Two modes, two policies, two risk levels.

### Pipeline Design

```
collection_editor_ai.py --content
  ↓ reads: collections + resources
  ↓ generates: intro, seo_title, seo_desc, faq_json
  ↓ writes: collection_content (published)
  ↓ review: batch audit via /admin/collection-detail.html

collection_editor_ai.py --editorial
  ↓ reads: collections + resources
  ↓ generates: editor_note, why_collect, audience, highlights
  ↓ writes: collection_content (draft, needs review)
  ↓ review: per-field via /admin/editorial-edit.html (Phase 9.3)
  ↓ publish: editor clicks "approve" → status becomes published
```

**Current `collection_editor_ai.py` only has `--content` mode.** Phase 9.1B will add `--editorial` mode using the prompts defined in this document.

### Usage

```bash
# SEO content (existing — auto-publish)
python3 collection_editor_ai.py --content

# Editorial content (Phase 9.1B — draft only)
python3 collection_editor_ai.py --editorial
python3 collection_editor_ai.py --editorial --limit 3    # test 3 collections
```

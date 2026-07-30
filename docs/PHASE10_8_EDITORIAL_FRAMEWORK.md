# Phase 10.8 — Editorial Resource Experience Framework

> Design proposal. No code.

---

## 1. Current Resource Detail Analysis

### What it does well

- Identifies the resource (title, format, size, platform)
- Provides a download link
- Links to related collections and resources
- Has SEO content (description, JSON-LD)

### What it doesn't do

- Tell the user WHY BigPRC selected this resource
- Help the user decide if this resource is right for them
- Build trust in BigPRC's curation judgment
- Give the user a reason to return

### The root problem

The current detail page treats resources as **data entries** (metadata + link). But BigPRC's value proposition is **editorial judgment**. The design expresses curation through visual polish, but the content doesn't deliver on that promise.

> A beautifully designed download page is still a download page.

---

## 2. New Information Architecture

### Editorial Layer (NEW)

```
┌─────────────────────────────────────────────┐
│ RESOURCE DETAIL                              │
├─────────────────────────────────────────────┤
│                                              │
│  TITLE                                        │
│  一句话描述 (from AI SEO data)                │
│                                              │
│  ┌───────────────────────────────────────┐   │
│  │ EDITOR'S TAKE                          │   │
│  │                                        │   │
│  │ 为什么推荐                              │   │
│  │                                        │   │
│  │ 1-3 sentences of editorial judgment.   │   │
│  │ Explains what makes this resource      │   │
│  │ worth keeping long-term.               │   │
│  │                                        │   │
│  │ 适合人群                                │   │
│  │                                        │   │
│  │ · 初学者 / 进阶用户 / 专业从业者        │   │
│  │ · 具体使用场景描述                      │   │
│  │                                        │   │
│  │ 推荐理由                                │   │
│  │                                        │   │
│  │ + 完整性高, 无需额外配置                 │   │
│  │ + 中文资源稀缺, 这份是目前最佳版本       │   │
│  │ + 持续更新, 社区活跃                     │   │
│  │                                        │   │
│  │ 注意事项 (optional)                     │   │
│  │                                        │   │
│  │ · 需要 XX 基础                           │   │
│  │ · 文件较大, 建议 WiFi 下载                │   │
│  └───────────────────────────────────────┘   │
│                                              │
│  ┌───────────────────────────────────────┐   │
│  │ QUICK FACTS                            │   │
│  │                                        │   │
│  │ 格式 · 大小 · 平台 · 版本               │   │
│  │ 收录时间 · 最后验证 · 编辑审核状态       │   │
│  └───────────────────────────────────────┘   │
│                                              │
│  [ CTA: 获取资源 ]                            │
│  收录于 BigPRC 数字资源策展库                  │
│                                              │
│  ┌───────────────────────────────────────┐   │
│  │ ABOUT THIS RESOURCE (SEO)              │   │
│  │                                        │   │
│  │ AI-generated detailed description      │   │
│  └───────────────────────────────────────┘   │
│                                              │
│  RELATED COLLECTIONS                          │
│  RELATED RESOURCES                            │
│                                              │
└─────────────────────────────────────────────┘
```

### Why this order

1. **Editor's Take first**: The first substantive content a user sees is editorial judgment. This immediately differentiates BigPRC from a file listing site.

2. **Quick Facts second**: Metadata is important but contextual — after the user understands WHY this resource matters, the facts about format/size become supporting information.

3. **CTA after editorial context**: The download button appears after the user has been given reasons to download. It's no longer a blind click.

4. **SEO content last**: The long-form AI description is valuable for search engines but not for human decision-making. It belongs at the bottom.

---

## 3. Field Design

### 3.1 Editor's Take — "编辑推荐"

| Field | Type | Required | Max Length | Source |
|-------|------|----------|------------|--------|
| `editor_recommendation` | text | ✅ | 200 chars | `collection_editor_ai.py` or manual |
| `target_audience` | text | ✅ | 100 chars | AI + editorial review |
| `strengths` | list[text] | ✅ | 3 items, 40 chars each | AI-generated, editor-approved |
| `caveats` | list[text] | — | 2 items, 40 chars each | Optional |

**Design principle**: Each field must answer a user question.

| Field | Answers |
|-------|---------|
| `editor_recommendation` | "Why is this worth my time?" |
| `target_audience` | "Is this for someone like me?" |
| `strengths` | "What makes this the best choice?" |
| `caveats` | "What should I know before downloading?" |

### 3.2 Quick Facts — "资源信息"

| Field | Source | Display |
|-------|--------|---------|
| Format | `category` from DB | Icon + label |
| Size | `size` from DB | Human-readable |
| Platform | `platform` from DB | Label |
| Version | `version` from DB | Label |
| Added date | `created_at` | "收录于 2024-03" |
| Last verified | `last_checked` | "链接验证于 2024-07" |
| Editorial status | `editorial_status` | Hidden from user; internal only |

**Design principle**: Quick Facts should fit in one visual scan. Current 4-field grid is already good — add "收录时间" and "最后验证" as small captions below.

### 3.3 Trust Signals — "策展标准"

These don't need to be on EVERY resource page. They can be:

**Option A**: A small line below the editor's take:
> "BigPRC 编辑根据长期价值、内容质量、用户体验三个维度筛选资源。了解我们的策展标准 →"

**Option B**: A dedicated `/curation` page linked from the footer.

**Recommendation: Option A on resource pages + Option B as a standalone page.** The inline signal builds immediate trust; the dedicated page provides depth for skeptical users.

---

## 4. Trust Page — `/curation`

### Purpose

Answer: "Why should I trust BigPRC's recommendations?"

### Structure (minimal)

```
BigPRC 策展标准

我们如何选择资源

长期价值
  不是一次性热门工具。
  我们选择经过时间验证、持续维护的资源。

内容质量
  信息准确、结构清晰、适合目标用户。
  不收录低质量搬运、广告嵌套、付费诱导内容。

用户体验
  获取流畅、文件完整、无需复杂配置。
  优先推荐有活跃社区或官方支持的项目。

编辑审核
  每个专题包含编辑视角（Editorial Note）。
  重点资源经过编辑单独推荐（Editor's Pick）。
  所有链接定期验证，失效及时更新或下架。

我们不做什么
  不追求收录数量。1760 个资源中，每个都经过筛选。
  不接受付费推广。所有推荐基于编辑判断。
  不存储文件。仅索引公开链接，尊重版权。
```

**Design**: Single page, clean layout, no decoration. Trust comes from clarity, not design flourishes.

---

## 5. Example Content

### Before (current)

```
BBC 自然纪录片合集

格式: 视频  |  大小: 42.5 GB  |  平台: 夸克网盘  |  版本: 2024

[ 夸克网盘 极速通道 ]
收录于 BigPRC 数字资源策展库

(Description text...)
```

### After (proposed)

```
BBC 自然纪录片合集
从《蓝色星球》到《地球脉动》，BBC 自然纪录片最完整的收藏版本。

编辑推荐
这可能是中文互联网上最完整的 BBC 自然纪录片合集。
收录了从 2001 年《蓝色星球》到 2023 年《地球脉动 III》
的全部主要系列，共 42.5GB。每一部都是原版高清。

适合
· 自然纪录片爱好者
· 家庭观影、亲子教育场景
· 地理/生物学科教师

推荐理由
+ 系列完整度高, 无需逐部寻找
+ 全部为原版高清, 非录制版
+ 中文双语字幕已内嵌

格式: 视频  ·  大小: 42.5 GB  ·  平台: 夸克网盘  ·  版本: 2024
收录于 2024-03  ·  链接验证于 2024-07

[ 夸克网盘 极速通道 ]
收录于 BigPRC 数字资源策展库  ·  了解策展标准 →

(Description text...)
```

---

## 6. SEO Impact

### Positive

- **Editor's Take adds unique content**: Each resource gets 150-300 words of original editorial text, not duplicated anywhere else on the web.
- **Structured data enhanced**: Add `review` schema for editorial recommendation.
- **Longer dwell time**: Users who read the editorial content spend more time on page — positive ranking signal.

### Neutral

- **Page length increases**: Editorial content adds ~500px of scroll. Acceptable — editorial pages benefit from depth.
- **CTA moves down**: Download button is now below editorial content. Compensated by higher click-through from informed users.

### Recommendation

Place a secondary CTA (text link) near the top for returning users who already know the resource and just want the link. The primary CTA stays after editorial content for new visitors.

---

## 7. Implementation Notes

### Data Source

The editorial fields (`editor_recommendation`, `target_audience`, `strengths`, `caveats`) can be:
1. AI-generated by `collection_editor_ai.py` (existing pipeline)
2. Stored in `collection_content` or a new `resource_editorial` table
3. Rendered conditionally — if not present, fall back to current layout

### Fallback

For resources without editorial content, the page falls back to the current layout (title → metadata → CTA → description). No empty editorial boxes.

### Gradual Rollout

1. Start with spotlight resources (already have editorial attention)
2. Expand to all resources in collections with published editorial status
3. Eventually cover all resources as AI pipeline scales

---

> **Framework complete. Awaiting confirmation to proceed with implementation.**

# Phase 9.4A — Editorial Detail Page Design

> **Status**: Design  
> **Depends on**: v0.9.3-stable (editorial.json)  

---

## 1. Page: `/admin/editorial-detail.html?id=<collection_id>`

**Purpose**: Single-collection editorial review. Read all four editorial fields, check completeness, see AI metadata. No writes.

**Entry points**:
- `editorial.html` — click collection title → `editorial-detail.html?id=bbc-nature`
- `collections.html` — (future) click Editorial status dot → same

---

## 2. Data Source

Single file: `/admin/data/editorial.json` (already exported by `collection_dashboard_export.py`).

```json
{
  "collections": [
    {
      "id": "bbc-nature",
      "title": "BBC 自然纪录片",
      "status": "complete",
      "has_editor_note": true,
      "has_why_collect": true,
      "has_audience": true,
      "has_highlights": true,
      "pct_complete": 100
    }
  ]
}
```

**Missing fields for this page**: editorial.json currently has boolean `has_*` fields but does NOT contain the actual text content. The detail page needs to show the text of editor_note, why_collect, audience, highlights.

**Solution**: Add 4 text fields to `build_editorial_status()` in `collection_dashboard_export.py`. Read from `collection_content` alongside the boolean checks.

```json
{
  "id": "bbc-nature",
  "title": "BBC 自然纪录片",
  "editor_note": "BBC自然纪录片系列...",
  "why_collect": "为自然爱好者提供...",
  "audience": "自然爱好者;纪录片收藏者;...",
  "highlights": ["《蓝色星球》...", "..."],
  ...
}
```

**Export change**: +4 lines in `build_editorial_status()` — add `cc.editor_note, cc.why_collect, cc.audience, cc.highlights` to the existing SELECT.

---

## 3. Page Layout

```
┌──────────────────────────────────────────────────┐
│  ← 返回编辑工作台                                  │
├──────────────────────────────────────────────────┤
│                                                  │
│  BBC 自然纪录片                                   │
│  bbc-nature  ·  315 资源  ·  🟢 已完成 (100%)     │
│                                                  │
│  ── 编辑推荐 ──────────────────────────────────  │
│  BBC自然纪录片系列将镜头对准地球的脉搏，从深海...    │
│  [🟢 已完成]                                      │
│                                                  │
│  ── 收藏理由 ──────────────────────────────────  │
│  为自然爱好者提供一个系统收藏BBC经典纪录片...       │
│  [🟢 已完成]                                      │
│                                                  │
│  ── 适合人群 ──────────────────────────────────  │
│  自然爱好者；纪录片收藏者；亲子教育家长...          │
│  [🟢 已完成]                                      │
│                                                  │
│  ── 精选亮点 ──────────────────────────────────  │
│  · 《完美星球》揭示地球系统精妙平衡                 │
│  · 《冰冻星球》极地生态的震撼记录                   │
│  · 《王朝》动物家族的权力与生存故事                 │
│  [🟢 已完成]                                      │
│                                                  │
│  ── AI Metadata ───────────────────────────────  │
│  数据导出: 2026-07-29T00:30:00 (12 分钟前)        │
│                                                  │
│  ── 快捷操作 ──────────────────────────────────  │
│  [🌐 前台页面]  [📚 专题管理]                      │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 4. Implementation

| File | Change | Lines |
|------|--------|-------|
| `collection_dashboard_export.py` | `build_editorial_status()`: add 4 text fields to SELECT | +4 |
| `admin/editorial-detail.html` | New: static HTML + fetch editorial.json | ~100 |

**Total: ~104 lines. Zero schema changes. Zero pipeline changes.**

---

## 5. Freeze Boundaries

| Constraint | Compliance |
|-----------|-----------|
| 只读页面 | ✅ fetch JSON only |
| 不写数据库 | ✅ no POST/PUT/DELETE |
| 不修改 collection_editor_ai.py | ✅ untouched |
| 不修改 schema | ✅ reads existing columns |
| 不新增 API | ✅ static JSON |
| 保持 Phase 9.3 冻结接口 | ✅ `editorial.json` schema is additive (4 new fields, no removals) |

---

确认后进入编码。
# Phase 9.3 — Editorial Dashboard Technical Design

> **Status**: Design Phase  
> **Depends on**: Rule Engine v0.8, Editorial Pipeline v0.9.2, Dashboard Phase 7  

---

## 一、已冻结接口 (Phase 9.3 不得修改)

| 接口 | 冻结版本 |
|------|---------|
| `rule_engine.match_collection()` | v0.8 |
| `rule_engine.parse_rule()` | v0.8 |
| `collection_editor_ai.py --editorial` | v0.9.2 |
| `parse_highlights()` | v0.9.1c |
| `ai_call()` retry chain | v0.9.1b |
| `collection_content` 表结构 | Phase 6 |
| `collections` 表结构 | Phase 5.3 |
| CLI → JSON → Static HTML | Phase 6 |

---

## 二、Editorial Dashboard 设计

### 2.1 解决哪些编辑工作？

| 编辑问题 | Dashboard 回答 |
|---------|---------------|
| "今天有哪些专题需要审核？" | 待审核计数 + 列表 |
| "哪些专题缺少编辑内容？" | 编辑完整度进度条 |
| "全站编辑进度如何？" | 完成率统计 |
| "从哪里开始工作？" | 快捷入口链接 |

### 2.2 首页统计信息

| 指标 | 数据来源 | 展示方式 |
|------|---------|---------|
| 待完善专题 | `editorial_status` — 任一字段为 NULL | 数字卡片 |
| 已完善专题 | 4/4 字段全部非空 | 数字卡片 |
| 内容完整度 | 各专题 `pct_complete` | 进度条列表 |
| 最近导出 | `generated_at` timestamp | 时间戳文本 |
| 快捷入口 | — | 链接到 editorial-detail、collections |

### 2.3 页面结构

新增 1 个页面，增强 1 个已有页面：

```
/admin/editorial.html          ← 新增: Editorial Dashboard
/admin/collections.html        ← 增强: 增加 editorial_status 列
```

(`/admin/collection-detail.html` 不修改 — 它是 Rule Debug Tool, 不承担 Editorial 职责)

### 2.4 各页面职责

#### `/admin/editorial.html` — Editorial Dashboard (新建)

- **功能**: 编辑工作台首页。展示全局编辑状态、待审核列表、完整度总览、快捷入口
- **数据来源**: `editorial.json` (由 `collection_dashboard_export.py` 新增导出)
- **操作流程**: 编辑打开 → 扫一眼完成率 → 点待完善专题 → 跳转 editorial-detail 页
- **涉及数据库**: 只读 `collection_content`
- **复用**: `collection_dashboard_export.py` 的 DB 连接和 query 模式; dashboard.html 的卡片样式

#### `/admin/collections.html` — 增强 (Phase 7 已有，增加 1 列)

- **功能**: 列表页增加 editorial_status 列 (绿色/红色圆点 × 4 字段)
- **数据来源**: `collections.json` (已有) + 新增 `editorial_status` 字段
- **操作流程**: 编辑扫描列表 → 看到红色字段 → 点击详情 → editorial-detail 页
- **复用**: 已有搜索/排序/筛选逻辑完全不动

### 2.5 最终页面总览

```
/admin/dashboard.html          Rule 总览 (Phase 7, 不修改)
/admin/collections.html        专题列表 + editorial 状态列 (Phase 9.3 增强)
/admin/collection-detail.html  Rule Debug Tool (Phase 8, 不修改)
/admin/editorial.html          Editorial Dashboard (Phase 9.3 新建)
/admin/collection-review.html  Discovery Review (Phase 5.3, 不修改)
```

---

## 三、数据设计

### 3.1 `editorial.json` Schema

由 `collection_dashboard_export.py` 新增函数 `build_editorial_status()` 导出：

```json
{
  "generated_at": "ISO timestamp",
  "summary": {
    "total": 16,
    "complete": 5,
    "incomplete": 11,
    "pct_overall": 31
  },
  "collections": [
    {
      "id": "bbc-nature",
      "title": "BBC 自然纪录片",
      "has_editor_note": false,
      "has_why_collect": false,
      "has_audience": false,
      "has_highlights": false,
      "pct_complete": 0,
      "editor_note_len": 0,
      "editor_note_lang": null
    }
  ]
}
```

### 3.2 数据来源

| 字段 | 来源 | 查询 |
|------|------|------|
| `has_editor_note` | `collection_content.editor_note IS NOT NULL AND != ''` | 已有字段，只读 |
| `has_why_collect` | 同上 | 同上 |
| `has_audience` | 同上 | 同上 |
| `has_highlights` | 同上 | 同上 |
| `pct_complete` | 4 个 has_* 中 true 的数量 / 4 × 100 | 计算值，不存储 |
| `editor_note_len` | `LENGTH(editor_note)` | 已有字段 |
| `editor_note_lang` | 通过检测前 100 字中 ASCII 占比判断 | 计算值，不存储 |

---

## 四、开发计划

### Phase 9.3A — Editorial Export + Collections Enhancement

**目标**: 数据层 — editorial.json 导出 + collections.html 增加编辑状态列

| 属性 | 值 |
|------|-----|
| **修改文件** | `collection_dashboard_export.py` (+50: `build_editorial_status()` 函数 + 导出 editorial.json) |
| **修改文件** | `collections.html` (+10: 增加 editorial_status 列) |
| **新增文件** | 无 |
| **数据库变更** | 无 |
| **预计代码量** | +60 行 |
| **风险** | 低 — 纯读取已有字段，JSON 增量导出 |
| **验收标准** | `python3 collection_dashboard_export.py` 生成 `editorial.json`; collections.html 每行显示 4 个绿色/红色圆点 |

### Phase 9.3B — Editorial Dashboard

**目标**: 页面 — editorial.html 工作台首页

| 属性 | 值 |
|------|-----|
| **修改文件** | 无 |
| **新增文件** | `admin/editorial.html` (~120 行) |
| **数据库变更** | 无 |
| **预计代码量** | +120 行 |
| **风险** | 低 — 纯 HTML + fetch JSON |
| **验收标准** | `/admin/editorial.html` 正确展示统计卡片、完成度列表、快捷入口 |

### Phase 9.3C — Freeze Phase 9.3

**目标**: 文档 + Tag

| 属性 | 值 |
|------|-----|
| **修改文件** | `docs/EDITORIAL_PIPELINE_ARCHITECTURE.md` (更新) |
| **新增文件** | 无 |
| **Tag** | `v0.9.3-stable` |
| **验收标准** | Editorial Dashboard 可支持编辑日常工作流 |

---

## 五、风险分析

| 风险 | 可能性 | 缓解 |
|------|--------|------|
| editorial.json 与 collections.json 数据不一致 | 低 | 同一 export 脚本生成，同一 DB session |
| collections.html 列过多 | 低 | 只增加 1 列（4 个圆点紧凑排列） |
| editorial.html 与 dashboard.html 职责重叠 | 低 | editorial.html 只看编辑内容；dashboard.html 只看规则健康。分层明确 |
| Phase 9.3B editorial-edit 页面需要写入能力 | 中 | 写入通过 CLI，不在此 Phase 范围。editorial.html 只做只读 |

---

确认后进入 Phase 9.3A 编码。
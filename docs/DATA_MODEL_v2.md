# BigPRC 数据模型 v2.0

> **版本**: v1.0
> **制定日期**: 2026-07-16
> **状态**: 设计稿，待实现
> **依赖**: [PRODUCT_CHARTER.md](PRODUCT_CHARTER.md)
>
> 本文档定义 BigPRC 从"资源列表站"升级为"数字资源策展平台"
> 所需的数据模型变更。先设计模型，再写代码。

---

## 1. 变更概览

### v1.x → v2.0 核心变化

| 维度 | v1.x (当前) | v2.0 (目标) |
|------|-----------|-----------|
| 资源属性 | 标题 + 链接 + 描述 | + 一句话定位(tagline) + 编辑字段 + AI 元数据 |
| 组织方式 | 单一分类(category) | 分类 + 多合集(Collections) |
| 编辑体系 | 无 | editor.status / editor.pick / editor.reason / editor.not_for |
| AI 角色 | SEO 描述生成 | 摘要 + 关键词 + 推荐理由候选 + SEO |
| 页面数据 | index.json (JS加载) | SSR 可直接渲染的结构化数据 |
| 数据源 | Excel 驱动 | Excel 同步 + 编辑可修改 |

### 设计原则

1. **向后兼容** — 现有 pipeline 不中断，用 ALTER TABLE 而非 DROP/CREATE
2. **字段先设计，数据后填充** — 新字段允许 NULL，逐步补数据
3. **一份数据，多端消费** — 同一个 resource 记录驱动首页、详情页、合集页、RSS
4. **编辑不阻塞** — editor 字段可空，空时使用 AI 生成默认值

---

## 2. 数据表设计

### 2.1 `resources` — 资源主表 (扩展)

```sql
-- 现有字段 (保持不变)
res_id          TEXT PRIMARY KEY,       -- e.g. "p001"
title           TEXT NOT NULL,          -- 资源标题
size            TEXT,                   -- 文件大小
normal_url      TEXT,                   -- 普通网盘链接
short_url       TEXT,                   -- 短链
seo_desc        TEXT,                   -- SEO 描述 (HTML)
category        TEXT,                   -- 分类 (e.g. "AI编程")
platform        TEXT,                   -- 平台 (e.g. "Mac,Windows")
version         TEXT,                   -- 版本号
password        TEXT,                   -- 提取码
rating          TEXT,                   -- 评分
sync_time       TIMESTAMP,              -- Excel 同步时间
ai_generated    INTEGER DEFAULT 0,      -- SEO 描述是否 AI 生成

-- v2.0 新增: 一句话定位
tagline         TEXT,                   -- 一句话定位 (e.g. "AI 驱动的终端开发助手")
                                        -- AI 可生成候选，编辑确认

-- v2.0 新增: 编辑体系
editor_status   TEXT DEFAULT 'pending', -- 'pending' | 'approved' | 'rejected'
editor_pick     INTEGER DEFAULT 0,      -- 1 = 编辑精选 (首页展示)
editor_reason   TEXT,                   -- 编辑推荐理由 (一句话)
editor_not_for  TEXT,                   -- 什么时候不用它 (边界说明)
editor_reviewed_at TIMESTAMP,           -- 编辑最后审核时间

-- v2.0 新增: AI 元数据
ai_summary      TEXT,                   -- AI 生成的短摘要 (50字以内)
ai_keywords     TEXT,                   -- AI 关键词 (JSON array string)
ai_reason_candidates TEXT,              -- AI 生成的推荐理由候选 (JSON array, 3-5条)
                                          -- 编辑可从中选择一条设为 editor_reason

-- v2.0 新增: 展示元数据
meta_platform   TEXT,                   -- 支持的平台 (结构化 JSON: ["Mac","Windows"])
meta_official_url TEXT,                 -- 官方网站
meta_language   TEXT,                   -- 语言 (e.g. "简体中文/English")
meta_license    TEXT,                   -- 许可证 (e.g. "开源/MIT", "免费", "付费")
meta_updated_at TEXT,                   -- 资源最后更新时间

-- v2.0 新增: 统计 (由脚本更新)
view_count      INTEGER DEFAULT 0,      -- 浏览量
click_count     INTEGER DEFAULT 0,      -- 点击量
score_popular   REAL DEFAULT 0.0,       -- 热度分 (计算字段, 定时更新)
```

### 2.2 `collections` — 合集表 (新建)

```sql
CREATE TABLE IF NOT EXISTS collections (
    id              TEXT PRIMARY KEY,       -- e.g. "mac-must-have"
    title           TEXT NOT NULL,          -- e.g. "Mac 必装软件"
    description     TEXT,                   -- e.g. "精选 Mac 平台上最值得安装的工具"
    cover_res_id    TEXT,                   -- 封面资源 ID (可选)
    sort_order      INTEGER DEFAULT 0,      -- 排序权重
    is_featured     INTEGER DEFAULT 0,      -- 是否在首页专题入口展示
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.3 `resource_collections` — 资源-合集关联表 (新建)

```sql
CREATE TABLE IF NOT EXISTS resource_collections (
    resource_id     TEXT NOT NULL,
    collection_id   TEXT NOT NULL,
    sort_order      INTEGER DEFAULT 0,      -- 在合集中的排序
    added_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (resource_id, collection_id),
    FOREIGN KEY (resource_id) REFERENCES resources(res_id),
    FOREIGN KEY (collection_id) REFERENCES collections(id)
);
```

---

## 3. 首页数据接口

`auto_generate.py` 渲染首页时需要从数据库查询以下数据集：

### 3.1 编辑精选 (editor_picks)

```sql
SELECT * FROM resources
WHERE editor_status = 'approved'
  AND editor_pick = 1
ORDER BY editor_reviewed_at DESC
LIMIT 2;
```
→ 输出到 `index.html` SSR 区块 "编辑精选"

### 3.2 热门工具 (hot)

```sql
SELECT * FROM resources
WHERE editor_status = 'approved'
ORDER BY score_popular DESC
LIMIT 6;
```
→ 输出到 `index.html` SSR 区块 "热门工具"

### 3.3 专题入口 (featured_collections)

```sql
SELECT * FROM collections
WHERE is_featured = 1
ORDER BY sort_order ASC
LIMIT 6;
```
→ 输出到 `index.html` SSR 区块 "专题推荐"

### 3.4 最新更新 (latest) — JS 异步加载

```sql
SELECT * FROM resources
ORDER BY sync_time DESC
LIMIT 4;
```
→ 输出到 `index.json` 或独立 API

### 3.5 站点统计 (异步)

```sql
SELECT COUNT(*) FROM resources WHERE editor_status = 'approved';
SELECT COUNT(*) FROM collections;
```
→ 首页 Footer 区域展示 (异步)

---

## 4. Excel 同步适配

`pantools_sync.py` 需要更新以支持新字段：

### Excel 新增列

| 列名 | 对应 DB 字段 | 说明 |
|------|-------------|------|
| 一句话定位 | `tagline` | 可选，AI 可补 |
| 合集 | `collection_ids` | 逗号分隔的合集 ID，同步时处理关联表 |
| 官方网站 | `meta_official_url` | 可选 |
| 语言 | `meta_language` | 可选 |
| 许可证 | `meta_license` | 可选 |
| 平台 | `meta_platform` | JSON 数组格式 |

### 同步逻辑变更

```
Excel 读取
  ↓
逐行处理:
  1. 写入/更新 resources 基础字段
  2. 如果 collection_ids 非空 → 更新 resource_collections 关联
  3. 如果 tagline 为空 → 标记为待 AI 生成
  ↓
返回同步统计
```

---

## 5. AI SEO 脚本适配

`ai_seo_writer.py` 需要扩展生成内容：

### 当前输出
- `seo_desc` (SEO 描述 HTML)

### v2.0 新增输出

| 输出字段 | 说明 | Prompt 指导 |
|---------|------|-----------|
| `ai_summary` | 50 字短摘要 | "用一句话说明这是什么工具" |
| `ai_keywords` | JSON 关键词数组 | "提取 5-8 个搜索关键词" |
| `ai_reason_candidates` | JSON 推荐理由候选 (3-5 条) | "从不同角度写推荐理由：功能角度、效率角度、替代角度" |
| `tagline` | 一句话定位 (仅当 Excel 未提供时) | "用 15 字以内定位这个工具" |

### 逻辑变更

```
对每条资源:
  1. 生成 seo_desc (已有)
  2. 生成 ai_summary
  3. 生成 ai_keywords → JSON
  4. 如果 tagline 为空 → 生成 tagline
  5. 生成 3-5 条推荐理由候选 → JSON
  写入 resources 表对应字段
```

---

## 6. 迁移计划

### 阶段 1: 数据库迁移 (无中断)

```sql
-- 所有变更都是 ALTER TABLE ADD COLUMN, 不影响现有数据和 pipeline
ALTER TABLE resources ADD COLUMN tagline TEXT;
ALTER TABLE resources ADD COLUMN editor_status TEXT DEFAULT 'pending';
ALTER TABLE resources ADD COLUMN editor_pick INTEGER DEFAULT 0;
ALTER TABLE resources ADD COLUMN editor_reason TEXT;
ALTER TABLE resources ADD COLUMN editor_not_for TEXT;
ALTER TABLE resources ADD COLUMN editor_reviewed_at TIMESTAMP;
ALTER TABLE resources ADD COLUMN ai_summary TEXT;
ALTER TABLE resources ADD COLUMN ai_keywords TEXT;
ALTER TABLE resources ADD COLUMN ai_reason_candidates TEXT;
ALTER TABLE resources ADD COLUMN meta_platform TEXT;
ALTER TABLE resources ADD COLUMN meta_official_url TEXT;
ALTER TABLE resources ADD COLUMN meta_language TEXT;
ALTER TABLE resources ADD COLUMN meta_license TEXT;
ALTER TABLE resources ADD COLUMN meta_updated_at TEXT;
ALTER TABLE resources ADD COLUMN view_count INTEGER DEFAULT 0;
ALTER TABLE resources ADD COLUMN click_count INTEGER DEFAULT 0;
ALTER TABLE resources ADD COLUMN score_popular REAL DEFAULT 0.0;

-- 新建表
CREATE TABLE IF NOT EXISTS collections (...);
CREATE TABLE IF NOT EXISTS resource_collections (...);
```

### 阶段 2: 脚本升级 (逐个文件)

| 顺序 | 文件 | 变更 |
|------|------|------|
| 1 | `pantools_sync.py` | 新增 Excel 列映射 + collections 关联 |
| 2 | `ai_seo_writer.py` | 新增 4 个 AI 输出字段 |
| 3 | `auto_generate.py` | 新增首页 SSR 渲染 + 首页数据查询 |
| 4 | `templates/index.html` | Jinja2 模板 (新文件) |

### 阶段 3: 数据回填 (可选)

已收录的 1,267 条资源运行一次 `ai_seo_writer.py all` 即可自动填充 `ai_summary`、`ai_keywords`、`ai_reason_candidates`。

编辑字段 (`editor_*`) 由人工逐步补充，不影响展示。

---

## 7. Collection 种子数据

系统启动时预置以下合集，后续编辑可增减：

```sql
INSERT INTO collections (id, title, description, is_featured, sort_order) VALUES
('ai-coding',     'AI 编程工具',     'AI 驱动的代码生成与开发辅助',          1, 1),
('mac-essentials','Mac 必装软件',    'Mac 用户最值得安装的效率工具',          1, 2),
('dev-toolkit',   '开发者工具箱',     '全栈开发、调试、部署必备',              1, 3),
('open-source',   '开源神器',         '值得关注的优质开源项目',                1, 4),
('creator-tools', '自媒体工具',       '内容创作、视频剪辑、设计素材',          1, 5),
('ai-models',     '本地大模型',       '可在本地运行的 LLM 与模型工具',         1, 6),
('learning',      '学习资源',         '编程、设计、AI 系统学习资料',           0, 7),
('design',        '设计素材与工具',    'UI/UX 设计资源、图标、字体、模板',      0, 8),
('nas-docker',    'NAS 与 Docker',   '自部署服务、家庭服务器、容器化应用',     0, 9);
```

---

## 附录: 字段对照速查

| 前端展示 | 数据来源 | 优先级 |
|---------|---------|--------|
| 首页 Hero Slogan | 静态 (模板) | — |
| 编辑精选卡片 | `editor_pick=1` 的 resources | P0 |
| 热门工具卡片 | `score_popular DESC` | P0 |
| 专题入口 | `is_featured=1` 的 collections | P0 |
| 详情页-标题 | `title` | — |
| 详情页-一句话定位 | `tagline` (有则用, 无则 AI 生成) | P2 |
| 详情页-为什么推荐 | `editor_reason` (有则用, 无则用 `ai_summary`) | P2 |
| 详情页-什么时候不用 | `editor_not_for` | P2 |
| 详情页-SEO 描述 | `seo_desc` | P3 |
| 合集页 | `collections JOIN resource_collections` | P3 |

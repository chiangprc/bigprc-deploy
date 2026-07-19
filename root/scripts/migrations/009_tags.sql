-- ============================================================
-- MIGRATION 009: 创建 Tags 标签系统 (P1-2)
-- Description: tags 标签词表 + resource_tags 多对多关联表
--              支撑搜索/专题/推荐/首页全部 P1 功能
-- Depends on:  008_validate_v2
-- ============================================================

-- Step 1: 标签词表
CREATE TABLE IF NOT EXISTS tags (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT    NOT NULL UNIQUE,
    slug    TEXT    NOT NULL UNIQUE,
    type    TEXT    DEFAULT 'topic',
    weight  REAL    DEFAULT 1.0,
    count   INTEGER DEFAULT 0
);

-- Step 2: 资源-标签关联表
CREATE TABLE IF NOT EXISTS resource_tags (
    resource_id TEXT    NOT NULL,
    tag_id      INTEGER NOT NULL,
    score       REAL    DEFAULT 0.5,
    source      TEXT    DEFAULT 'ai',
    PRIMARY KEY (resource_id, tag_id),
    FOREIGN KEY (resource_id) REFERENCES resources(res_id),
    FOREIGN KEY (tag_id)      REFERENCES tags(id)
);

-- Step 3: 索引
CREATE INDEX IF NOT EXISTS idx_tags_slug   ON tags(slug);
CREATE INDEX IF NOT EXISTS idx_tags_type   ON tags(type);
CREATE INDEX IF NOT EXISTS idx_tags_count  ON tags(count DESC);
CREATE INDEX IF NOT EXISTS idx_rt_tag      ON resource_tags(tag_id);
CREATE INDEX IF NOT EXISTS idx_rt_resource ON resource_tags(resource_id);

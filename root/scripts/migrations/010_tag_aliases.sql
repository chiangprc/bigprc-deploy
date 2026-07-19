-- ============================================================
-- MIGRATION 010: Tag 治理层 (P1-2.5)
-- Description: tag_aliases 别名表 + tags 增加 type/parent_id
--              Phase 1: 品牌统一 + 拼写修复 (不激进合并)
-- ============================================================

-- Step 1: 标签别名表 (碎片 → 标准)
CREATE TABLE IF NOT EXISTS tag_aliases (
    alias   TEXT PRIMARY KEY,
    target  TEXT NOT NULL,
    reason  TEXT DEFAULT 'auto'
);

-- Step 2: tags 增加分类字段
ALTER TABLE tags ADD COLUMN parent_id INTEGER REFERENCES tags(id);
ALTER TABLE tags ADD COLUMN tag_type  TEXT DEFAULT 'topic';

-- Step 3: 索引
CREATE INDEX IF NOT EXISTS idx_ta_target   ON tag_aliases(target);
CREATE INDEX IF NOT EXISTS idx_tags_type   ON tags(tag_type);
CREATE INDEX IF NOT EXISTS idx_tags_parent ON tags(parent_id);

-- ============================================================
-- MIGRATION 011: Tag 层级字段补充
-- Description: 补上 tags.parent_id + tags.tag_type
--              Phase 2 标签分类体系的基础
-- Depends on:  010_tag_aliases
-- ============================================================

ALTER TABLE tags ADD COLUMN parent_id INTEGER REFERENCES tags(id);
ALTER TABLE tags ADD COLUMN tag_type  TEXT DEFAULT 'topic';

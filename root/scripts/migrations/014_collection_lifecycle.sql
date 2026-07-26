-- MIGRATION 014: 专题生命周期 (Phase 5.3A)
-- 仅包含本阶段实际使用的字段

ALTER TABLE collections ADD COLUMN status         TEXT DEFAULT 'published';
ALTER TABLE collections ADD COLUMN merged_into    TEXT REFERENCES collections(id);
ALTER TABLE collections ADD COLUMN auto_generated INTEGER DEFAULT 0;

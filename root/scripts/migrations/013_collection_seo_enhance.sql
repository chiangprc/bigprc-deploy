-- ============================================================
-- MIGRATION 013: 专题 SEO 编辑策展层 (Phase 4.1)
-- Description: collection_content 新增策展编辑字段
--              editor_note / why_collect / audience / highlights
-- Depends on:  012_collection_rules
-- ============================================================

ALTER TABLE collection_content ADD COLUMN editor_note TEXT;
ALTER TABLE collection_content ADD COLUMN why_collect  TEXT;
ALTER TABLE collection_content ADD COLUMN audience     TEXT;
ALTER TABLE collection_content ADD COLUMN highlights   TEXT;

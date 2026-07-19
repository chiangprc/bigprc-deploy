-- ============================================================
-- MIGRATION 012: 合集规则字段 + 自动生成支持
-- Description: collections 增加 rule_json, 支持 tag 规则匹配
--               resource_collections 增加 score 列
-- Depends on:  011_tag_hierarchy
-- ============================================================

ALTER TABLE collections ADD COLUMN rule_json TEXT;
ALTER TABLE resource_collections ADD COLUMN score REAL DEFAULT 0.0;

-- ============================================================
-- MIGRATION 002: 扩展 resources 表至 v2
-- Description: 新增列 + 数据迁移
--               normal_url → source_url (语义重命名)
--               size → file_size (语义重命名)
--               sync_time → updated_at (语义重命名)
--               新增 status 列 (资源存续状态)
--               旧字段全部保留 (Phase D 之前不删除)
--
-- 注意: CHECK 约束需要通过重建表实现, 风险太高。
--       对 resources.status 采用应用层校验 (migration.py validate).
--       resource_content.editor_status 的 CHECK 在新表建表时生效 (003).
--
-- Depends on:  001_create_schema_version
-- Rollback:    恢复 migration 前备份
-- ============================================================

-- Step 1: 新增列 (全部允许 NULL，不破坏已有数据)

ALTER TABLE resources ADD COLUMN status TEXT DEFAULT 'active';
ALTER TABLE resources ADD COLUMN source_url TEXT;
ALTER TABLE resources ADD COLUMN official_url TEXT;
ALTER TABLE resources ADD COLUMN file_size TEXT;
ALTER TABLE resources ADD COLUMN language TEXT;
ALTER TABLE resources ADD COLUMN license TEXT;
ALTER TABLE resources ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE resources ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Step 2: 数据迁移 — 旧值复制到新列

UPDATE resources SET source_url = normal_url;
UPDATE resources SET file_size = size;
UPDATE resources SET updated_at = sync_time;
UPDATE resources SET created_at = sync_time;
UPDATE resources SET status = 'active' WHERE status IS NULL;

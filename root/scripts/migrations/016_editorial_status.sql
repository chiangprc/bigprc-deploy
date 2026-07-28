-- MIGRATION 016: Editorial Workflow Status (Phase 9.4B)
-- Additive only. Idempotent. Safe defaults.

ALTER TABLE collection_content ADD COLUMN editorial_status TEXT DEFAULT 'draft';
ALTER TABLE collection_content ADD COLUMN reviewed_at      TIMESTAMP;
ALTER TABLE collection_content ADD COLUMN approved_at      TIMESTAMP;

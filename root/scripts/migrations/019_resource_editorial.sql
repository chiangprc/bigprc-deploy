-- MIGRATION 019: Resource Editorial Layer (Phase 10.8)
-- Editor's Take system — editorial judgment for individual resources.
-- All new columns DEFAULT NULL. Zero impact on existing resources.
-- Editorial content renders only when editorial_status = 'published'.
--
-- Depends on:  018_spotlight
-- Rollback:    restore pre-migration backup (migration.py backup auto-creates)

ALTER TABLE resources ADD COLUMN editor_recommendation TEXT;
ALTER TABLE resources ADD COLUMN target_audience TEXT;
ALTER TABLE resources ADD COLUMN strengths TEXT;          -- JSON array, e.g. '["item1","item2"]'
ALTER TABLE resources ADD COLUMN caveats TEXT;             -- JSON array
ALTER TABLE resources ADD COLUMN editorial_status TEXT DEFAULT NULL;
ALTER TABLE resources ADD COLUMN reviewed_at TEXT DEFAULT NULL;
ALTER TABLE resources ADD COLUMN generated_at TEXT DEFAULT NULL;
ALTER TABLE resources ADD COLUMN ai_model TEXT DEFAULT NULL;

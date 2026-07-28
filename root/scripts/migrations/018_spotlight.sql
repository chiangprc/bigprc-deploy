-- MIGRATION 018: Resource Spotlight (Phase 10.2)
-- Editor-curated featured resources within collections.
-- Additive only. DEFAULT 0. All existing rows unaffected.

ALTER TABLE resource_collections ADD COLUMN spotlight INTEGER DEFAULT 0;

-- MIGRATION 017: Set existing editorial content to 'published'
-- All 16 collections with editor_note written → default to published.
-- New collections created after this migration start at 'draft'.

UPDATE collection_content
SET editorial_status = 'published'
WHERE editor_note IS NOT NULL AND editor_note != ''
  AND (editorial_status IS NULL OR editorial_status = 'draft');

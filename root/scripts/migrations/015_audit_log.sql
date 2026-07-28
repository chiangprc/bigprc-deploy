-- MIGRATION 015: Collection Audit Log (Phase 9.4B)
-- Records all editorial status transitions for rollback + history.

CREATE TABLE IF NOT EXISTS collection_audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id   TEXT NOT NULL,
    action          TEXT NOT NULL,
    old_status      TEXT,
    new_status      TEXT,
    operator        TEXT DEFAULT 'editor',
    metadata        TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cal_collection ON collection_audit_log(collection_id);
CREATE INDEX IF NOT EXISTS idx_cal_created   ON collection_audit_log(created_at);

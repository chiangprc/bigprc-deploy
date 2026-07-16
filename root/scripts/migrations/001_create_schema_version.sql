-- ============================================================
-- MIGRATION 001: 创建版本追踪表
-- Description: 建立 _migrations 表，用于追踪所有已执行的迁移
-- Depends on:  nothing
-- Rollback:    DROP TABLE IF EXISTS _migrations
-- ============================================================

CREATE TABLE IF NOT EXISTS _migrations (
    version     INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    checksum    TEXT,
    applied_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status      TEXT DEFAULT 'applied'
);

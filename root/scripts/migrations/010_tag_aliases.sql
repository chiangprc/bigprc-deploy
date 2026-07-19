-- ============================================================
-- MIGRATION 010: 创建 Tag 治理层 (P1-2.5)
-- Description: tag_aliases 别名表 — 碎片标签 → 标准标签映射
--              自动归一: BBC纪录片→BBC, 野生动物→动物, 道家→道教
-- ============================================================

CREATE TABLE IF NOT EXISTS tag_aliases (
    alias   TEXT PRIMARY KEY,   -- 碎片标签名 (如 "BBC纪录片")
    target  TEXT NOT NULL,      -- 标准标签名 (如 "BBC")
    reason  TEXT DEFAULT 'auto' -- auto/manual
);

CREATE INDEX IF NOT EXISTS idx_ta_target ON tag_aliases(target);

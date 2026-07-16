-- ============================================================
-- MIGRATION 003: 创建 resource_content 内容层
-- Description: 从 resources 表拆分出 SEO/编辑/AI 内容字段
--              旧字段保留在 resources 中不删除，本表为 v2 新表
-- Depends on:  002_resources_v2
-- Rollback:    恢复 migration 前备份
-- ============================================================

-- Step 1: 建表 (含 CHECK 约束)

CREATE TABLE IF NOT EXISTS resource_content (
    resource_id          TEXT PRIMARY KEY,
    tagline              TEXT,
    seo_desc             TEXT,
    ai_generated         INTEGER DEFAULT 0,
    ai_summary           TEXT,
    ai_keywords          TEXT,
    ai_reason_candidates TEXT,
    editor_status        TEXT DEFAULT 'draft'
                          CHECK(editor_status IN ('draft','pending','approved','rejected')),
    editor_pick          INTEGER DEFAULT 0,
    editor_reason        TEXT,
    editor_not_for       TEXT,
    editor_reviewed_at   TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resources(res_id)
);

-- Step 2: 从旧 resources 表迁移已有数据

INSERT OR IGNORE INTO resource_content (resource_id, seo_desc, ai_generated, editor_status)
SELECT res_id, seo_desc, ai_generated,
       CASE WHEN seo_desc IS NOT NULL AND seo_desc != '' THEN 'approved' ELSE 'draft' END
FROM resources;

-- 已有 SEO 描述的资源视为已审核 (approved)，其余为草稿 (draft)

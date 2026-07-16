-- ============================================================
-- MIGRATION 005: 创建 resource_access 访问入口表
-- Description: 支持一个资源多个访问入口 (官网/GitHub/网盘/镜像)
--              原 resources.password 迁移至本表
--              原 resources.normal_url/short_url 同时写入本表
-- Depends on:  004_resource_metrics
-- Rollback:    恢复 migration 前备份
-- ============================================================

CREATE TABLE IF NOT EXISTS resource_access (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id  TEXT NOT NULL,
    type         TEXT NOT NULL,
    url          TEXT NOT NULL,
    password     TEXT,
    priority     INTEGER DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resources(res_id)
);

-- 从 resources 迁移: normal_url → type='source'
INSERT OR IGNORE INTO resource_access (resource_id, type, url, password, priority)
SELECT res_id, 'source', normal_url, password, 1
FROM resources
WHERE normal_url IS NOT NULL AND normal_url != '';

-- 从 resources 迁移: short_url → type='short'
INSERT OR IGNORE INTO resource_access (resource_id, type, url, password, priority)
SELECT res_id, 'short', short_url, password, 2
FROM resources
WHERE short_url IS NOT NULL AND short_url != '';

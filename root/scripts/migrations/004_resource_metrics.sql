-- ============================================================
-- MIGRATION 004: 创建 resource_metrics 行为数据表
-- Description: 独立的行为统计数据表，支持未来调整热度公式
--              原 resources.rating 迁移至 rating_score
-- Depends on:  003_resource_content
-- Rollback:    恢复 migration 前备份
-- ============================================================

CREATE TABLE IF NOT EXISTS resource_metrics (
    resource_id   TEXT PRIMARY KEY,
    view_count    INTEGER DEFAULT 0,
    click_count   INTEGER DEFAULT 0,
    fav_count     INTEGER DEFAULT 0,
    score         REAL DEFAULT 0.0,
    rating_score  REAL DEFAULT 0.0,
    rating_count  INTEGER DEFAULT 0,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resources(res_id)
);

-- 为已有资源初始化 metrics 行
INSERT OR IGNORE INTO resource_metrics (resource_id, rating_score)
SELECT res_id,
       CASE WHEN rating IS NOT NULL AND rating != ''
            THEN CAST(rating AS REAL)
            ELSE 0.0
       END
FROM resources;

-- 评分从 resources.rating 迁移，旧字段保留

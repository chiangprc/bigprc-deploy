-- ============================================================
-- MIGRATION 007: 创建性能索引
-- Description: 首页查询、SEO 筛选、合集关联的索引
-- Depends on:  006_collections
-- Rollback:    恢复 migration 前备份
-- ============================================================

-- 首页: 编辑精选 + 热门排序
CREATE INDEX IF NOT EXISTS idx_content_editor_pick
    ON resource_content(editor_pick, editor_status);

-- 首页: 按热度分排序
CREATE INDEX IF NOT EXISTS idx_metrics_score
    ON resource_metrics(score DESC);

-- 列表: 按更新时间排序 (最新资源)
CREATE INDEX IF NOT EXISTS idx_resources_updated
    ON resources(updated_at DESC);

-- 合集: 资源关联查询
CREATE INDEX IF NOT EXISTS idx_rc_resource
    ON resource_collections(resource_id);

-- 合集: 合集内资源列表
CREATE INDEX IF NOT EXISTS idx_rc_collection
    ON resource_collections(collection_id);

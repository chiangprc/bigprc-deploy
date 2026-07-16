-- ============================================================
-- MIGRATION 008: 数据完整性验证
-- Description: 检查新表结构、数据关联、索引是否完整
--               所有检查应返回 0 (无问题)
-- Depends on:  007_indexes
-- Rollback:    N/A (只读检查，不修改数据)
-- ============================================================

-- Check 1: 核心表是否存在 (由 migration.py 执行时检查)
-- 此 SQL 文件中的每条查询，结果 > 0 表示有问题

-- Check 2: 孤儿 resource_content (不应存在)
-- 预期结果: 0
SELECT COUNT(*) AS orphan_content_count
FROM resource_content
WHERE resource_id NOT IN (SELECT res_id FROM resources);

-- Check 3: 孤儿 resource_metrics (不应存在)
-- 预期结果: 0
SELECT COUNT(*) AS orphan_metrics_count
FROM resource_metrics
WHERE resource_id NOT IN (SELECT res_id FROM resources);

-- Check 4: 孤儿 resource_access (不应存在)
-- 预期结果: 0
SELECT COUNT(*) AS orphan_access_count
FROM resource_access
WHERE resource_id NOT IN (SELECT res_id FROM resources);

-- Check 5: 孤儿合集关联 (不应存在)
-- 预期结果: 0
SELECT COUNT(*) AS orphan_collection_ref_count
FROM resource_collections
WHERE resource_id NOT IN (SELECT res_id FROM resources);

-- Check 6: 资源与内容数量是否一致
-- 预期结果: 0
SELECT ABS(
    (SELECT COUNT(*) FROM resources) -
    (SELECT COUNT(*) FROM resource_content)
) AS resource_content_mismatch;

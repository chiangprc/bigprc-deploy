-- ============================================================
-- MIGRATION 006: 创建合集体系 (collections + content + join)
-- Description: 合集定义、合集 SEO 内容、资源-合集关联
--               预置 9 个种子合集
-- Depends on:  005_resource_access
-- Rollback:    恢复 migration 前备份
-- ============================================================

-- 合集定义表
CREATE TABLE IF NOT EXISTS collections (
    id           TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    description  TEXT,
    cover_res_id TEXT,
    sort_order   INTEGER DEFAULT 0,
    is_featured  INTEGER DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 合集 SEO 内容表
CREATE TABLE IF NOT EXISTS collection_content (
    collection_id  TEXT PRIMARY KEY,
    intro          TEXT,
    seo_title      TEXT,
    seo_desc       TEXT,
    faq_json       TEXT,
    FOREIGN KEY (collection_id) REFERENCES collections(id)
);

-- 资源-合集关联表
CREATE TABLE IF NOT EXISTS resource_collections (
    resource_id    TEXT NOT NULL,
    collection_id  TEXT NOT NULL,
    sort_order     INTEGER DEFAULT 0,
    added_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (resource_id, collection_id),
    FOREIGN KEY (resource_id) REFERENCES resources(res_id),
    FOREIGN KEY (collection_id) REFERENCES collections(id)
);

-- 种子数据: 9 个合集
INSERT OR IGNORE INTO collections (id, title, description, is_featured, sort_order) VALUES
('ai-coding',      'AI 编程工具',      'AI 驱动的代码生成与开发辅助',           1, 1),
('mac-essentials', 'Mac 必装软件',     'Mac 用户最值得安装的效率工具',           1, 2),
('dev-toolkit',    '开发者工具箱',     '全栈开发、调试、部署必备',               1, 3),
('open-source',    '开源神器',         '值得关注的优质开源项目',                 1, 4),
('creator-tools',  '自媒体工具',       '内容创作、视频剪辑、设计素材',           1, 5),
('ai-models',      '本地大模型',       '可在本地运行的 LLM 与模型工具',          1, 6),
('learning',       '学习资源',         '编程、设计、AI 系统学习资料',            0, 7),
('design',         '设计素材与工具',    'UI/UX 设计资源、图标、字体、模板',       0, 8),
('nas-docker',     'NAS 与 Docker',    '自部署服务、家庭服务器、容器化应用',      0, 9);

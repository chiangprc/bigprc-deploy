# BigPRC 数据库迁移计划 v1.0

> **版本**: v1.0
> **制定日期**: 2026-07-17
> **状态**: 待执行
> **依赖**: [PRODUCT_CHARTER.md](PRODUCT_CHARTER.md)／[DATA_MODEL_v2.md](DATA_MODEL_v2.md)
>
> 本文档定义 v1 资源站 → v2 内容产品的数据库迁移步骤。
> **核心原则：双轨运行——旧系统不中断，新字段逐步填充，新模板逐步启用。**

---

## 1. 当前数据库现状

### 1.1 部署信息

| 项目 | 值 |
|------|------|
| 数据库路径 (VPS) | `/root/scripts/database.db` |
| 数据库引擎 | SQLite 3 |
| 当前大小 | ~4.5 MB |
| 资源数量 | ~1,267 条 |
| 备份路径 | `/root/scripts/database.db.bak` (最后备份 2026-07-01) |
| Crontab 备份 | 每天 2:00 AM `/root/scripts/backup.sh` |

### 1.2 当前表结构 (`resources`)

```sql
CREATE TABLE resources (
    res_id       TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    size         TEXT,
    normal_url   TEXT,          -- 网盘链接 ← v2 重命名
    short_url    TEXT,          -- 短链     ← v2 重命名
    seo_desc     TEXT,          -- SEO 描述  ← v2 迁移到 resource_content
    category     TEXT,
    platform     TEXT,
    version      TEXT,
    password     TEXT,
    rating       TEXT,
    sync_time    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ai_generated INTEGER DEFAULT 0
);
```

### 1.3 当前写入者

| 脚本 | 写入内容 |
|------|---------|
| `pantools_sync.py` | INSERT/UPDATE 全量字段 (UPSERT by res_id) |
| `ai_seo_writer.py` | UPDATE seo_desc, ai_generated |
| `auto_generate.py` | 只读 (SELECT * FROM resources) |

### 1.4 当前读取者

| 消费者 | 读取内容 | 输出 |
|--------|---------|------|
| `auto_generate.py` | SELECT * FROM resources | 全站 HTML + sitemap + jump_rules |
| 首页 `index.html` | fetch `/index.json` | JS 动态渲染搜索 |
| 详情页 | Jinja2 模板变量 | 每个资源的 HTML |
| 列表页 | fetch `/index.json` | JS 分页表格 |

---

## 2. v2.0 目标结构

### 2.1 表拆分策略

```
v1:  resources (13 columns, 单表)

              ▼

v2:  resources           — 核心实体 (不变字段)
     resource_content    — 内容层 (SEO/编辑/AI)
     resource_metrics    — 行为数据 (浏览/点击/热度)
     collections         — 合集定义
     collection_content  — 合集 SEO 内容
     resource_collections — 资源-合集关联
```

### 2.2 表定义

#### `resources` — 核心实体 (精简)

```sql
CREATE TABLE resources (
    res_id       TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    category     TEXT,
    platform     TEXT,               -- 保留兼容，逐步废弃
    version      TEXT,
    password     TEXT,
    rating       TEXT,

    -- v2: URL 语义化
    source_url   TEXT,               -- 原 normal_url (资源来源)
    short_url    TEXT,               -- 短链 (保留)
    official_url TEXT,               -- 官方网站 (新增)

    -- v2: 状态机
    status       TEXT DEFAULT 'pending',  -- draft | pending | approved | archived

    -- v2: 元数据
    language     TEXT,               -- 语言
    license      TEXT,               -- 许可证
    file_size    TEXT,               -- 文件大小 (原 size, 重命名更明确)

    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `resource_content` — 内容层

```sql
CREATE TABLE resource_content (
    resource_id          TEXT PRIMARY KEY,
    tagline              TEXT,       -- 一句话定位 (15字)
    seo_desc             TEXT,       -- SEO 描述 HTML (从旧表迁移)
    ai_generated         INTEGER DEFAULT 0,
    ai_summary           TEXT,       -- AI 短摘要
    ai_keywords          TEXT,       -- AI 关键词 (JSON array)
    ai_reason_candidates TEXT,       -- AI 推荐理由候选 (JSON array)
    editor_status        TEXT DEFAULT 'draft',  -- draft | pending | approved | rejected
    editor_pick          INTEGER DEFAULT 0,
    editor_reason        TEXT,       -- 编辑推荐理由
    editor_not_for       TEXT,       -- 什么时候不用
    editor_reviewed_at   TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resources(res_id)
);
```

#### `resource_metrics` — 行为数据

```sql
CREATE TABLE resource_metrics (
    resource_id  TEXT PRIMARY KEY,
    view_count   INTEGER DEFAULT 0,
    click_count  INTEGER DEFAULT 0,
    fav_count    INTEGER DEFAULT 0,
    score        REAL DEFAULT 0.0,   -- 热度分 = views*0.3 + clicks*0.4 + favs*0.3
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (resource_id) REFERENCES resources(res_id)
);
```

#### `collections` — 合集定义

```sql
CREATE TABLE collections (
    id           TEXT PRIMARY KEY,       -- e.g. "mac-must-have"
    title        TEXT NOT NULL,          -- e.g. "Mac 必装软件"
    description  TEXT,
    cover_res_id TEXT,
    sort_order   INTEGER DEFAULT 0,
    is_featured  INTEGER DEFAULT 0,     -- 首页专题入口
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `collection_content` — 合集 SEO 内容

```sql
CREATE TABLE collection_content (
    collection_id  TEXT PRIMARY KEY,
    intro          TEXT,               -- 合集介绍
    seo_title      TEXT,               -- 独立 SEO 标题
    seo_desc       TEXT,               -- SEO 描述
    faq_json       TEXT,               -- FAQ (JSON)
    FOREIGN KEY (collection_id) REFERENCES collections(id)
);
```

#### `resource_collections` — 关联表

```sql
CREATE TABLE resource_collections (
    resource_id    TEXT NOT NULL,
    collection_id  TEXT NOT NULL,
    sort_order     INTEGER DEFAULT 0,
    added_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (resource_id, collection_id),
    FOREIGN KEY (resource_id) REFERENCES resources(res_id),
    FOREIGN KEY (collection_id) REFERENCES collections(id)
);
```

### 2.3 状态机职责分离

| 字段 | 表 | 含义 | 可选值 |
|------|-----|------|--------|
| `status` | `resources` | 资源存续状态 | `active` / `archived` / `deleted` |
| `editor_status` | `resource_content` | 内容编辑流程 | `draft` / `pending` / `approved` / `rejected` |

> **首页展示条件**: `resources.status = 'active' AND resource_content.editor_status = 'approved'`
>
> 旧数据迁移时: `resources.status` 默认 'active', `resource_content.editor_status` 默认 'approved' (已有内容视为已审核)

### 2.4 字段映射: v1 → v2

| v1 字段 | v2 表.字段 | 说明 |
|---------|-----------|------|
| `res_id` | `resources.res_id` | 不变 |
| `title` | `resources.title` | 不变 |
| `size` | `resources.file_size` | 重命名 |
| `normal_url` | `resources.source_url` | 重命名，同时写入 `resource_access` |
| `short_url` | `resources.short_url` | 不变，同时写入 `resource_access` |
| `seo_desc` | `resource_content.seo_desc` | 迁移到内容层 |
| `category` | `resources.category` | 不变 |
| `platform` | `resources.platform` | 保留兼容 |
| `version` | `resources.version` | 不变 |
| `password` | `resource_access.password` | **移出主表**，作为入口属性 |
| `rating` | `resource_metrics.rating_score` | **移出主表**，作为用户行为数据 |
| `sync_time` | `resources.updated_at` | 重命名 |
| `ai_generated` | `resource_content.ai_generated` | 迁移到内容层 |
| — | `resources.official_url` | 新增 |
| — | `resources.status` | 新增 (生命周期: active/archived/deleted) |
| — | `resource_content.*` | 新增 (tagline, ai_*, editor_*) |
| — | `resource_metrics.*` | 新增 |
| — | `resource_access.*` | 新增 (多入口支持) |

---

## 3. 迁移策略：双轨运行

### 3.1 原则

```
旧表 resources (13 columns)  ←── pantools_sync.py (继续工作)
                                      │
新表 resources (16 columns)   ←── 同一个 UPSERT, 额外填充
新表 resource_content         ←── 从旧表迁移 + AI 填充
新表 resource_metrics         ←── 初始化为 0
新表 collections              ←── 种子数据
```

**关键承诺**：
- `auto_generate.py` **不改读旧字段**，直到新字段验证通过
- 旧 `index.html` 继续服务，直到新 `index.html` (Jinja2) 测试通过
- 所有迁移 SQL 可回滚（`migration.py down`）

### 3.2 切换步骤

```
Phase 0: Shadow Read (影子读取, 新增)
  └── 创建 test_new_generator.py 读 v2 表
  └── 输出与旧 auto_generate.py 对比
  └── 确认资源数量一致、内容完整、无孤儿数据
  └── 通过 → 进入 Phase A

Phase A: 数据库扩展 (零影响)
  └── python3 migration.py plan → 审查
  └── python3 migration.py backup → 强制备份
  └── python3 migration.py up → 执行 001-008
  └── python3 migration.py validate → 全部 PASS
  └── 旧 pipeline 完全不受影响

Phase B: 脚本升级 (逐步)
  └── pantools_sync.py → 同时写新旧字段
  └── ai_seo_writer.py → 填充 resource_content
  └── auto_generate.py → 新增首页查询 (不影响旧页面)

Phase C: 模板切换 (原子操作)
  └── 新 index.html (Jinja2) 部署
  └── 旧 index.html 重命名为 index_old.html (保留 7 天)
  └── 观察流量、SEO、错误日志

Phase D: 清理 (稳定后)
  └── 删除旧 resources 表中已迁移的冗余字段
  └── 删除 index_old.html
```

### 3.3 回滚方案

每步都有反向操作：

| 步骤 | 回滚方式 |
|------|---------|
| 新建表 | `DROP TABLE IF EXISTS` (无数据损失) |
| ALTER TABLE | 新字段允许 NULL，回滚 = 忽略新字段 |
| 脚本升级 | `git checkout` 旧版本脚本 |
| 模板切换 | 恢复旧 `index.html` |

---

## 4. Migration 系统设计

### 4.1 文件结构

```
root/scripts/
├── migration.py                    ← 迁移管理器
└── migrations/
    ├── 001_create_schema_version.sql  ← _migrations 版本追踪表
    ├── 002_resources_v2.sql           ← resources 新列 + CHECK 约束 + 数据迁移
    ├── 003_resource_content.sql       ← resource_content 表 + seo_desc 迁移
    ├── 004_resource_metrics.sql       ← resource_metrics 表 + rating 迁移
    ├── 005_resource_access.sql        ← resource_access 表 + password 迁移
    ├── 006_collections.sql            ← collections + collection_content + resource_collections
    ├── 007_indexes.sql                ← 性能索引
    └── 008_validate_v2.sql            ← 数据完整性检查
```

### 4.2 `migration.py` 设计

```python
#!/usr/bin/env python3
"""
BigPRC 数据库迁移管理器

数据库路径: 从 /root/scripts/.env 读取 DB_FILE
  VPS 生产: DB_FILE=/root/scripts/database.db
  本地开发: DB_FILE=./database.db

用法:
  python3 migration.py status        # 查看当前版本和待执行迁移
  python3 migration.py plan          # DRY-RUN: 显示迁移计划，不执行
  python3 migration.py up            # 执行所有未执行的迁移 (自动备份 → 执行 → validate)
  python3 migration.py validate      # 运行 008_validate_v2 数据完整性检查
  python3 migration.py backup        # 仅备份，不迁移

流程:
  status/plan → 审查
  backup      → 强制备份 (也包含在 up 中自动执行)
  up          → 自动备份 → 逐条执行 → 写 _migrations 表 → validate
  validate    → 5 项检查全部 PASS 才算成功

回滚策略:
  不提供逐条反向 SQL (SQLite DROP COLUMN 兼容性不可靠)。
  回滚方式: 恢复迁移前自动备份的 .db 文件。
  备份路径: /root/backups/pre_migration_YYYYMMDD_HHMMSS.db
```

### 4.3 `migration.py` 输出示例

```
$ python3 migration.py status
Current version: 0 (no migrations applied)
Pending: 001, 002, 003, 004, 005, 006, 007, 008

$ python3 migration.py plan
=== Migration Plan (DRY-RUN) ===

Backup will be created at:
  /root/backups/pre_migration_20260717_120000.db

Migrations to execute:
  001_create_schema_version.sql
  002_resources_v2.sql           (ALTER TABLE + UPDATE ~1267 rows)
  003_resource_content.sql       (CREATE TABLE + INSERT ~1267 rows)
  004_resource_metrics.sql       (CREATE TABLE + INSERT ~1267 rows)
  005_resource_access.sql        (CREATE TABLE + INSERT from password/urls)
  006_collections.sql            (CREATE 3 tables + 9 seed rows)
  007_indexes.sql                (CREATE 5 indexes)
  008_validate_v2.sql            (5 integrity checks)

WARNING: No changes will be made. Use 'up' to execute.

$ python3 migration.py up
[1/8] 001_create_schema_version.sql ... OK
[2/8] 002_resources_v2.sql ............ OK (1267 rows)
[3/8] 003_resource_content.sql ........ OK (1267 rows)
[4/8] 004_resource_metrics.sql ........ OK (1267 rows)
[5/8] 005_resource_access.sql ......... OK
[6/8] 006_collections.sql ............ OK (9 collections)
[7/8] 007_indexes.sql ................ OK (5 indexes)
[8/8] 008_validate_v2.sql ............ ALL PASS
Migration complete. Version: 008

$ python3 migration.py validate
✅ resources: 1267 rows
✅ resource_content: 1267 rows (linked)
✅ resource_metrics: 1267 rows (linked)
✅ resource_access: N rows (linked)
✅ collections: 9 rows
✅ orphan resources: 0
✅ orphan collection refs: 0
ALL CHECKS PASSED
```

import os
import sys
import sqlite3
import hashlib
from datetime import datetime

DB_FILE = os.getenv("DB_FILE", "/root/scripts/database.db")
MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")
BACKUP_DIR = "/root/backups"

# 迁移版本表 (放在数据库内)
SCHEMA_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS _migrations (
    version     TEXT PRIMARY KEY,
    name        TEXT,
    checksum    TEXT,
    applied_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status      TEXT DEFAULT 'applied'
);
"""
```

### 4.3 迁移文件格式

每份 SQL 文件头部包含元信息：

```sql
-- === MIGRATION: 001_extend_resources ===
-- Description: 扩展 resources 表，新增 v2 字段
-- Depends on:  nothing (baseline)
-- Rollback:    ALTER TABLE resources DROP COLUMN ... (manual review)
-- Applied at:  (auto-filled by migration.py)

-- UP:
ALTER TABLE resources ADD COLUMN source_url TEXT;
ALTER TABLE resources ADD COLUMN official_url TEXT;
ALTER TABLE resources ADD COLUMN status TEXT DEFAULT 'pending';
ALTER TABLE resources ADD COLUMN language TEXT;
ALTER TABLE resources ADD COLUMN license TEXT;
ALTER TABLE resources ADD COLUMN file_size TEXT;
ALTER TABLE resources ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE resources ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- DATA MIGRATION: copy existing values
UPDATE resources SET source_url = normal_url;
UPDATE resources SET file_size = size;
UPDATE resources SET updated_at = sync_time;
UPDATE resources SET status = 'approved';

-- DOWN (manual review required):
-- ALTER TABLE resources DROP COLUMN source_url;
-- ...
```

---

## 5. 迁移顺序

| # | 文件 | 内容 | CHECK 约束 |
|---|------|------|-----------|
| 1 | `001_create_schema_version.sql` | 创建 `_migrations` 版本追踪表 | — |
| 2 | `002_resources_v2.sql` | ALTER TABLE 新增列 + 数据迁移 + CHECK(status) | `CHECK(status IN ('active','archived','deleted'))` |
| 3 | `003_resource_content.sql` | 创建 resource_content + 迁移 seo_desc/ai_generated + CHECK(editor_status) | `CHECK(editor_status IN ('draft','pending','approved','rejected'))` |
| 4 | `004_resource_metrics.sql` | 创建 resource_metrics + 迁移 rating | — |
| 5 | `005_resource_access.sql` | 创建 resource_access + 迁移 password/normal_url/short_url | — |
| 6 | `006_collections.sql` | 创建 collections + collection_content + resource_collections + 9 条种子数据 | — |
| 7 | `007_indexes.sql` | 创建 5 个性能索引 | — |
| 8 | `008_validate_v2.sql` | 5 项数据完整性检查 | — |

> **旧字段不删除**: 所有 v1 字段 (normal_url, size, password, rating, sync_time, seo_desc) 在 Phase D 之前保留。新脚本同时读写新旧字段。旧 auto_generate.py 不受影响。

### 5.1 关键索引 (007)

```sql
-- SEO 查询: 按编辑状态筛选
CREATE INDEX idx_content_editor_status ON resource_content(editor_status);

-- 首页热门: 按热度分排序
CREATE INDEX idx_metrics_score ON resource_metrics(score DESC);

-- 最新资源: 按更新时间排序
CREATE INDEX idx_resources_updated ON resources(updated_at DESC);

-- 合集关联查询
CREATE INDEX idx_rc_resource ON resource_collections(resource_id);
CREATE INDEX idx_rc_collection ON resource_collections(collection_id);
```

### 5.2 数据完整性验证 (008)

```sql
-- 检查 1: 资源与内容 1:1 对应
SELECT 'orphan_content' AS check_name, COUNT(*) AS issue_count
FROM resource_content WHERE resource_id NOT IN (SELECT res_id FROM resources);

-- 检查 2: 资源与 metrics 1:1 对应
SELECT 'orphan_metrics' AS check_name, COUNT(*) AS issue_count
FROM resource_metrics WHERE resource_id NOT IN (SELECT res_id FROM resources);

-- 检查 3: 合集关联无孤儿
SELECT 'orphan_collection_ref' AS check_name, COUNT(*) AS issue_count
FROM resource_collections WHERE resource_id NOT IN (SELECT res_id FROM resources);

-- 检查 4: 数量一致性
SELECT 'count_mismatch' AS check_name,
       ABS((SELECT COUNT(*) FROM resources) - (SELECT COUNT(*) FROM resource_content)) AS issue_count;

-- 检查 5: 访问入口无孤儿
SELECT 'orphan_access' AS check_name, COUNT(*) AS issue_count
FROM resource_access WHERE resource_id NOT IN (SELECT res_id FROM resources);

-- 所有检查应返回 issue_count = 0
```

---

## 6. 备份策略

### 迁移前 (强制执行)

```bash
# 1. SQLite 备份
sqlite3 /root/scripts/database.db ".backup /root/backups/pre_migration_$(date +%Y%m%d_%H%M%S).db"

# 2. 常规备份 (已有)
/root/scripts/backup.sh

# 3. Schema 快照
sqlite3 /root/scripts/database.db ".schema" > /root/backups/schema_$(date +%Y%m%d_%H%M%S).sql
```

### 迁移后验证

```sql
-- 验证脚本
SELECT COUNT(*) FROM resources;                    -- 应 = 迁移前数量
SELECT COUNT(*) FROM resource_content;             -- 应 = resources 数量
SELECT COUNT(*) FROM resource_metrics;             -- 应 = resources 数量
SELECT COUNT(*) FROM collections;                  -- 应 = 9
SELECT COUNT(*) FROM _migrations WHERE status='applied'; -- 应 = 6
```

---

## 7. 风险矩阵

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 迁移 SQL 语法错误 | 低 | 高 | 先在测试 DB 上执行，验证通过再上生产 |
| 旧脚本读取已删除字段 | 中 | 高 | 不删旧字段，只新增；旧脚本不改读逻辑 |
| 数据迁移丢失或截断 | 低 | 高 | 备份优先，逐条验证 COUNT |
| 新字段与旧逻辑冲突 | 低 | 中 | 新字段全部允许 NULL |
| VPS 磁盘不足 | 低 | 中 | 备份后压缩；当前 17GB 可用，新增 <= 10MB |
| migration.py 本身 bug | 中 | 中 | 支持 dry-run 模式；每步后验证 |

---

## 8. 后续 TODO

- [ ] 在本地创建测试 DB (从 VPS 拉 `database.db`)
- [ ] 编写 `migration.py`
- [ ] 编写 6 个 SQL 迁移文件
- [ ] 本地测试：`migration.py up` → 验证 → `migration.py down`
- [ ] VPS 备份 → 执行迁移 → 验证
- [ ] 升级 `pantools_sync.py` (双写新旧字段)
- [ ] 升级 `ai_seo_writer.py` (填充 resource_content)
- [ ] 升级 `auto_generate.py` (新增首页查询)
- [ ] 创建 `templates/index.html` (Jinja2)
- [ ] 切换首页

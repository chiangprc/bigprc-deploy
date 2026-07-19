#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BigPRC 数据库迁移管理器 v1.0

数据库路径: 从 /root/scripts/.env 读取 DB_FILE
  VPS 生产: DB_FILE=/root/scripts/database.db
  本地开发: DB_FILE=./database.db

用法:
  python3 migration.py status        # 查看当前版本和待执行迁移
  python3 migration.py plan          # DRY-RUN: 显示迁移计划，不执行
  python3 migration.py up            # 执行所有未执行迁移 (自动备份 → 执行 → validate)
  python3 migration.py validate      # 运行数据完整性检查
  python3 migration.py backup        # 仅备份数据库

流程 (up):
  读取 .env → 获取 DB_FILE
  → 创建 _migrations 表 (如果不存在)
  → 扫描 migrations/ 目录，找出未执行的 .sql 文件
  → 强制备份数据库到 /root/backups/
  → 逐文件执行，每条 SQL 都在事务中
  → 记录执行结果到 _migrations 表
  → 运行 validate

回滚策略:
  不提供逐条反向 SQL。回滚 = 恢复 up 之前自动创建的 .backup 文件。
  备份路径: /root/backups/pre_migration_YYYYMMDD_HHMMSS.db
"""

import os
import sys
import sqlite3
import hashlib
import re
import time
from datetime import datetime
from pathlib import Path

# ============================================================
# 配置
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = SCRIPT_DIR / "migrations"
BACKUP_DIR = Path("/root/backups")

# 数据库路径: 优先从 .env 读取，否则使用默认值
def _load_db_path():
    env_file = SCRIPT_DIR / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("DB_FILE="):
                    val = line.split("=", 1)[1].strip()
                    return val
    # 默认值
    return "/root/scripts/database.db"

DB_FILE = _load_db_path()

# ============================================================
# 工具函数
# ============================================================

def _connect(db_path=None):
    """连接数据库"""
    path = db_path or DB_FILE
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def _ensure_migrations_table(conn):
    """确保 _migrations 版本追踪表存在"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            version     INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            checksum    TEXT,
            applied_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status      TEXT DEFAULT 'applied'
        )
    """)
    conn.commit()

def _get_applied_versions(conn):
    """获取已应用的迁移版本号列表"""
    _ensure_migrations_table(conn)
    rows = conn.execute(
        "SELECT version FROM _migrations WHERE status = 'applied' ORDER BY version"
    ).fetchall()
    return [r[0] for r in rows]

def _scan_migrations():
    """扫描 migrations/ 目录，返回 [(version, name, filepath), ...]"""
    if not MIGRATIONS_DIR.exists():
        return []

    migrations = []
    for f in sorted(MIGRATIONS_DIR.iterdir()):
        if f.suffix != '.sql':
            continue
        match = re.match(r'^(\d{3})_(.+)\.sql$', f.name)
        if not match:
            continue
        version = int(match.group(1))
        name = f.name
        migrations.append((version, name, f))

    return sorted(migrations, key=lambda x: x[0])

def _checksum(filepath):
    """计算文件 SHA256"""
    with open(filepath, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def _parse_sql_statements(filepath):
    """解析 .sql 文件，返回 SQL 语句列表 (跳过注释和空行)"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 移除单行注释
    lines = []
    for line in content.split('\n'):
        stripped = line.strip()
        # 跳过空行和纯注释行
        if not stripped or stripped.startswith('--'):
            continue
        # 移除行内注释
        if '--' in line:
            line = line.split('--')[0]
        lines.append(line)

    text = ' '.join(lines)
    # 按分号分割
    statements = [s.strip() for s in text.split(';') if s.strip()]
    return statements

def _backup():
    """备份数据库"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"pre_migration_{timestamp}.db"

    import shutil
    shutil.copy2(DB_FILE, backup_path)

    size_mb = backup_path.stat().st_size / (1024 * 1024)
    return backup_path, size_mb

# ============================================================
# 命令实现
# ============================================================

def cmd_status():
    """查看当前版本状态"""
    conn = _connect()
    try:
        applied = _get_applied_versions(conn)
        current = max(applied) if applied else 0
        migrations = _scan_migrations()
        pending = [m for m in migrations if m[0] > current]

        print(f"Database: {DB_FILE}")
        print(f"Current version: {current}")

        if applied:
            print(f"Applied: {', '.join(str(v) for v in applied)}")
        else:
            print("Applied: (none)")

        if pending:
            print(f"Pending ({len(pending)}): {', '.join(str(m[0]) for m in pending)}")
        else:
            print("Pending: (none — up to date)")

        return 0
    finally:
        conn.close()

def cmd_plan():
    """DRY-RUN: 显示迁移计划，不执行"""
    conn = _connect()
    try:
        applied = _get_applied_versions(conn)
        current = max(applied) if applied else 0
        migrations = _scan_migrations()
        pending = [m for m in migrations if m[0] > current]

        if not pending:
            print("No pending migrations. Database is up to date.")
            return 0

        print("=" * 60)
        print("  Migration Plan (DRY-RUN — no changes will be made)")
        print("=" * 60)
        print()
        print(f"Database: {DB_FILE}")
        print(f"Current version: {current}")
        print(f"Pending: {len(pending)} migrations")
        print()
        print(f"Backup will be created at:")
        print(f"  {BACKUP_DIR}/pre_migration_{{timestamp}}.db")
        print()
        print("Migrations to execute:")

        for version, name, filepath in pending:
            stmts = _parse_sql_statements(filepath)
            print(f"  {version:03d}  {name}")
            for stmt in stmts[:3]:  # 最多显示前 3 条
                preview = stmt[:80].replace('\n', ' ')
                print(f"       {preview}...")
            if len(stmts) > 3:
                print(f"       ... and {len(stmts) - 3} more statements")
        print()
        print("WARNING: No changes were made. Use 'up' to execute.")

        return 0
    finally:
        conn.close()

def cmd_backup():
    """仅备份数据库"""
    print(f"Database: {DB_FILE}")
    backup_path, size_mb = _backup()
    print(f"Backup created: {backup_path}")
    print(f"Size: {size_mb:.1f} MB")
    return 0

def cmd_up():
    """执行所有未执行的迁移"""
    conn = _connect()
    try:
        _ensure_migrations_table(conn)
        applied = _get_applied_versions(conn)
        current = max(applied) if applied else 0
        migrations = _scan_migrations()
        pending = [m for m in migrations if m[0] > current]

        if not pending:
            print("No pending migrations. Database is up to date.")
            return 0

        print("=" * 60)
        print("  BigPRC Database Migration")
        print("=" * 60)
        print(f"Database: {DB_FILE}")
        print(f"From version {current} → {max(m[0] for m in pending)}")
        print(f"Pending: {len(pending)} migrations")
        print()

        # 强制备份
        print("[backup] Creating backup...")
        backup_path, size_mb = _backup()
        print(f"[backup] {backup_path} ({size_mb:.1f} MB)")
        print()

        # 逐文件执行
        total_ok = 0
        total_fail = 0

        for version, name, filepath in pending:
            stmts = _parse_sql_statements(filepath)
            cs = _checksum(filepath)
            tag = f"[{version:03d}/{max(m[0] for m in pending):03d}]"

            print(f"{tag} {name} ({len(stmts)} statements)...", end=' ', flush=True)

            try:
                for stmt in stmts:
                    conn.execute(stmt)

                # 记录执行成功
                conn.execute(
                    "INSERT INTO _migrations (version, name, checksum, status) VALUES (?, ?, ?, 'applied')",
                    (version, name, cs)
                )
                conn.commit()
                print("OK")
                total_ok += 1

            except Exception as e:
                conn.rollback()
                print(f"FAILED")
                print(f"       Error: {e}")

                # 记录失败
                try:
                    conn.execute(
                        "INSERT INTO _migrations (version, name, checksum, status) VALUES (?, ?, ?, 'failed')",
                        (version, name, cs)
                    )
                    conn.commit()
                except Exception:
                    pass

                total_fail += 1
                print(f"       Rolled back. Fix the error and re-run 'up'.")
                break

        print()
        print(f"Result: {total_ok} OK, {total_fail} FAILED")

        if total_fail > 0:
            print(f"Backup available at: {backup_path}")
            print("To restore: copy the backup file over database.db")
            return 1

        # 自动 validate
        print()
        return cmd_validate()

    finally:
        conn.close()

def cmd_validate():
    """运行数据完整性检查"""
    conn = _connect()
    try:
        print("=" * 60)
        print("  Data Integrity Validation")
        print("=" * 60)
        print()

        all_pass = True
        checks = []

        # 检查 1: 核心表存在
        required_tables = [
            'resources',
            'resource_content',
            'resource_metrics',
            'resource_access',
            'collections',
            'collection_content',
            'resource_collections',
            'tags',
            'resource_tags',
            '_migrations',
        ]

        existing_tables = set(
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        )

        for table in required_tables:
            ok = table in existing_tables
            checks.append(('table_exists', table, ok))
            all_pass = all_pass and ok

        # 检查 2: 数据关联 (孤儿检查)
        orphan_checks = [
            ('orphan_content',
             "SELECT COUNT(*) FROM resource_content WHERE resource_id NOT IN (SELECT res_id FROM resources)"),
            ('orphan_metrics',
             "SELECT COUNT(*) FROM resource_metrics WHERE resource_id NOT IN (SELECT res_id FROM resources)"),
            ('orphan_access',
             "SELECT COUNT(*) FROM resource_access WHERE resource_id NOT IN (SELECT res_id FROM resources)"),
            ('orphan_collection_ref',
             "SELECT COUNT(*) FROM resource_collections WHERE resource_id NOT IN (SELECT res_id FROM resources)"),
        ]

        for check_name, sql in orphan_checks:
            try:
                count = conn.execute(sql).fetchone()[0]
                ok = (count == 0)
                checks.append((check_name, f"{count} orphans", ok))
                all_pass = all_pass and ok
            except Exception as e:
                checks.append((check_name, f"error: {e}", False))
                all_pass = False

        # 检查 3: 数量一致性
        try:
            res_count = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
            content_count = conn.execute("SELECT COUNT(*) FROM resource_content").fetchone()[0]
            metrics_count = conn.execute("SELECT COUNT(*) FROM resource_metrics").fetchone()[0]

            ok = (res_count == content_count == metrics_count)
            checks.append(('count_match',
                          f"resources={res_count} content={content_count} metrics={metrics_count}", ok))
            all_pass = all_pass and ok
        except Exception as e:
            checks.append(('count_match', f"error: {e}", False))
            all_pass = False

        # 检查 4: 索引存在
        required_indexes = [
            'idx_content_editor_pick',
            'idx_metrics_score',
            'idx_resources_updated',
            'idx_rc_resource',
            'idx_rc_collection',
            'idx_tags_slug',
            'idx_tags_type',
            'idx_tags_count',
            'idx_rt_tag',
            'idx_rt_resource',
        ]

        existing_indexes = set(
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        )

        for idx in required_indexes:
            ok = idx in existing_indexes
            checks.append(('index_exists', idx, ok))
            all_pass = all_pass and ok

        # 检查 5: migration 状态
        applied = _get_applied_versions(conn)
        checks.append(('migration_count', f"{len(applied)} applied", len(applied) > 0))

        # 输出结果
        for category, detail, ok in checks:
            icon = "✅" if ok else "❌"
            label = category.replace('_', ' ').title()
            print(f"  {icon} {label}: {detail}")

        print()
        if all_pass:
            print("ALL CHECKS PASSED")
        else:
            print("SOME CHECKS FAILED — review above")

        return 0 if all_pass else 1

    finally:
        conn.close()

# ============================================================
# 入口
# ============================================================

COMMANDS = {
    'status':   cmd_status,
    'plan':     cmd_plan,
    'up':       cmd_up,
    'validate': cmd_validate,
    'backup':   cmd_backup,
}

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: python3 migration.py <command>")
        print()
        print("Commands:")
        print("  status     Show current version and pending migrations")
        print("  plan       Dry-run: show what will be executed")
        print("  up         Execute all pending migrations (backup → run → validate)")
        print("  validate   Run data integrity checks")
        print("  backup     Create database backup only")
        print()
        print(f"Database: {DB_FILE}")
        print(f"Migrations: {MIGRATIONS_DIR}")
        sys.exit(1)

    cmd = COMMANDS[sys.argv[1]]
    sys.exit(cmd())

if __name__ == "__main__":
    main()

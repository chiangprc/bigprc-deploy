# -*- coding: utf-8 -*-
"""
BigPRC pantools_sync.py v2.0 — Excel → v2 数据模型同步器

升级 (v1 → v2):
  - 数据库结构由 migration.py 管理, 本脚本只验证不建表
  - 双写: resources (新旧字段) + resource_content + resource_access
          + resource_metrics + resource_collections
  - password → resource_access (不再写 resources)
  - rating → resource_metrics.rating_score (float 转换)
  - 合集同步: Excel "合集" 列 → resource_collections
  - --dry-run: 预览变更

用法:
  python3 pantools_sync.py              # 正常同步
  python3 pantools_sync.py --dry-run    # 预览模式
"""

import os
import sys
import sqlite3
import openpyxl
from dotenv import load_dotenv

# ============================================================
# 1. 配置
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

EXCEL_FILE = os.getenv("EXCEL_FILE", "/root/scripts/pantools_export.xlsx")
DB_FILE    = os.getenv("DB_FILE", "/root/scripts/database.db")
DRY_RUN    = "--dry-run" in sys.argv

# ============================================================
# 2. Excel 列名映射 (改列名只改这里)
# ============================================================

FIELD_MAP = {
    "title":        "文件名",
    "category":     "资源类型",
    "platform":     "适用平台",
    "version":      "版本号",
    "source_url":   "链接",
    "short_url":    "短链",
    "tagline":      "一句话定位",
    "official_url": "官方网站",
    "license":      "许可证",
    "language":     "语言",
    "password":     "解压密码",
    "rating":       "推荐星级",
    "size":         "文件大小",
    "seo_desc":     "SEO简介",
    "ai_generated": "AI生成",
    "collections":  "合集",
}

# ============================================================
# 3. 数据库验证 (替代旧 init_db — 不建表, 不 ALTER)
# ============================================================

REQUIRED_TABLES = ["resources"]
V2_TABLES = ["resource_content", "resource_metrics", "resource_access",
             "collections", "collection_content", "resource_collections"]

def check_db(conn):
    existing = set(r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall())

    for t in REQUIRED_TABLES:
        if t not in existing:
            print(f"❌ 缺少核心表: {t}")
            print("   请先运行: python3 migration.py up")
            sys.exit(1)

    missing_v2 = [t for t in V2_TABLES if t not in existing]
    if missing_v2:
        print(f"⚠️  v2 表未创建, 将跳过 v2 写入: {', '.join(missing_v2)}")
        print("   运行 migration.py up 后恢复\n")

    return existing

# ============================================================
# 4. Excel 读取
# ============================================================

def load_excel():
    print(f"📥 读取数据源: {EXCEL_FILE}")
    wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
    sheet = wb.active
    header = {cell.value.strip(): idx for idx, cell in enumerate(sheet[1]) if cell.value}
    rows = list(sheet.iter_rows(min_row=2, values_only=True))
    print(f"   {len(rows)} 行数据")
    return header, rows

# ============================================================
# 5. 数据提取
# ============================================================

def safe_str(row, header, key, default=None):
    excel_col = FIELD_MAP.get(key)
    if not excel_col or excel_col not in header:
        return default
    v = row[header[excel_col]]
    if v is None:
        return default
    s = str(v).strip()
    return default if s.lower() in ("none", "", "-") else s

def safe_bool(row, header, key):
    v = safe_str(row, header, key)
    if v is None:
        return 0
    return 1 if v.lower() in ("1", "yes", "是", "true") else 0

def parse_rating(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    star_count = s.count("★") + s.count("☆") * 0.5
    if star_count > 0:
        return star_count
    try:
        return float(s)
    except ValueError:
        return None

def extract_row(row, header):
    title = safe_str(row, header, "title")
    if not title:
        return None

    source_url = safe_str(row, header, "source_url")
    short_url  = safe_str(row, header, "short_url")
    if not source_url and not short_url:
        return None

    collections_raw = safe_str(row, header, "collections")
    collection_ids = []
    if collections_raw:
        collection_ids = [c.strip() for c in collections_raw.split(",") if c.strip()]

    return {
        "title":        title,
        "category":     safe_str(row, header, "category"),
        "platform":     safe_str(row, header, "platform"),
        "version":      safe_str(row, header, "version"),
        "source_url":   source_url,
        "short_url":    short_url,
        "official_url": safe_str(row, header, "official_url"),
        "tagline":      safe_str(row, header, "tagline"),
        "license":      safe_str(row, header, "license"),
        "language":     safe_str(row, header, "language"),
        "password":     safe_str(row, header, "password"),
        "size":         safe_str(row, header, "size", "N/A"),
        "seo_desc":     safe_str(row, header, "seo_desc"),
        "ai_generated": safe_bool(row, header, "ai_generated"),
        "rating_raw":   safe_str(row, header, "rating"),
        "rating_float": parse_rating(safe_str(row, header, "rating")),
        "collections":  collection_ids,
    }

# ============================================================
# 6. 同步函数 (每张表一个函数)
# ============================================================

def sync_resources(cursor, res_id, d):
    """resources 表: v1 字段 + v2 新字段, 双写

       v1 保留: normal_url, size, seo_desc, category, platform, version, sync_time
       v2 新增: source_url, official_url, file_size, language, license, updated_at
       password/rating → 不再写 resources, 由 sync_access/sync_metrics 处理
    """
    existing_cols = set(r[1] for r in cursor.connection.execute(
        "PRAGMA table_info(resources)"
    ).fetchall())

    cols = ["res_id"]
    vals = [res_id]

    # v1 字段 (旧字段保留, password/rating 设 NULL)
    field_defs = [
        ("title",        d["title"]),
        ("size",         d["size"]),
        ("normal_url",   d["source_url"]),
        ("short_url",    d["short_url"]),
        ("seo_desc",     d["seo_desc"]),
        ("category",     d["category"]),
        ("platform",     d["platform"]),
        ("version",      d["version"]),
        ("password",     None),
        ("rating",       None),
        ("ai_generated", d["ai_generated"]),
    ]
    for col, val in field_defs:
        if col in existing_cols:
            cols.append(col)
            vals.append(val)

    # v2 新字段 (migration 002 后存在)
    v2_defs = [
        ("source_url",   d["source_url"]),
        ("official_url", d["official_url"]),
        ("file_size",    d["size"]),
        ("language",     d["language"]),
        ("license",      d["license"]),
    ]
    for col, val in v2_defs:
        if col in existing_cols:
            cols.append(col)
            vals.append(val)

    placeholders = ", ".join(["?"] * len(vals))
    col_list = ", ".join(cols)

    update_parts = []
    for col in cols:
        if col == "res_id":
            continue
        if col == "seo_desc":
            update_parts.append(
                "seo_desc=CASE WHEN excluded.seo_desc IS NULL OR excluded.seo_desc = '' "
                "THEN resources.seo_desc ELSE excluded.seo_desc END")
        else:
            update_parts.append(f"{col}=excluded.{col}")

    if "sync_time" in existing_cols:
        update_parts.append("sync_time=CURRENT_TIMESTAMP")
    if "updated_at" in existing_cols:
        update_parts.append("updated_at=CURRENT_TIMESTAMP")

    cursor.execute(f'''
        INSERT INTO resources ({col_list}) VALUES ({placeholders})
        ON CONFLICT(res_id) DO UPDATE SET {", ".join(update_parts)}
    ''', vals)
    return cursor.rowcount

def sync_content(cursor, res_id, d):
    """resource_content: tagline + seo_desc + ai_generated
       不自动 approve, 不填默认文案"""
    cursor.execute('''
        INSERT INTO resource_content (resource_id, tagline, seo_desc, ai_generated)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(resource_id) DO UPDATE SET
            tagline      = COALESCE(excluded.tagline, resource_content.tagline),
            seo_desc     = COALESCE(excluded.seo_desc, resource_content.seo_desc),
            ai_generated = excluded.ai_generated
    ''', (res_id, d["tagline"], d["seo_desc"], d["ai_generated"]))
    has_tagline = 1 if d["tagline"] else 0
    return cursor.rowcount, has_tagline

def sync_access(cursor, res_id, d):
    """resource_access: source_url + short_url + password"""
    stats = {"source": 0, "short": 0, "password": 0}

    if d["source_url"]:
        cursor.execute('''
            INSERT OR IGNORE INTO resource_access (resource_id, type, url, password, priority)
            VALUES (?, 'source', ?, ?, 1)
        ''', (res_id, d["source_url"], d["password"]))
        stats["source"] = cursor.rowcount

    if d["short_url"]:
        cursor.execute('''
            INSERT OR IGNORE INTO resource_access (resource_id, type, url, password, priority)
            VALUES (?, 'short', ?, ?, 2)
        ''', (res_id, d["short_url"], d["password"]))
        stats["short"] = cursor.rowcount

    if d["password"]:
        cursor.execute('''
            UPDATE resource_access SET password=? WHERE resource_id=?
        ''', (d["password"], res_id))
        stats["password"] = cursor.rowcount

    return stats

def sync_metrics(cursor, res_id, d):
    """resource_metrics: rating_score (float)"""
    cursor.execute('''
        INSERT INTO resource_metrics (resource_id, rating_score)
        VALUES (?, ?)
        ON CONFLICT(resource_id) DO UPDATE SET rating_score = excluded.rating_score
    ''', (res_id, d["rating_float"] or 0.0))
    has_rating = 1 if d["rating_float"] is not None else 0
    return cursor.rowcount, has_rating

def sync_collections(cursor, res_id, d, existing_ids):
    """resource_collections: 仅关联已存在的合集, 不自动创建"""
    linked, skipped = 0, []
    for cid in d["collections"]:
        if cid in existing_ids:
            cursor.execute('''
                INSERT OR IGNORE INTO resource_collections (resource_id, collection_id)
                VALUES (?, ?)
            ''', (res_id, cid))
            if cursor.rowcount > 0:
                linked += 1
        else:
            skipped.append(cid)
    return linked, skipped

# ============================================================
# 7. 主流程
# ============================================================

def main():
    if DRY_RUN:
        print("🔍 DRY-RUN 模式 — 仅预览, 不修改数据库\n")

    header, rows = load_excel()
    conn = sqlite3.connect(DB_FILE)
    existing_tables = check_db(conn)
    cursor = conn.cursor()

    has_content    = "resource_content"      in existing_tables
    has_access     = "resource_access"       in existing_tables
    has_metrics    = "resource_metrics"      in existing_tables
    has_collection = "resource_collections"  in existing_tables

    existing_collection_ids = set()
    if "collections" in existing_tables:
        existing_collection_ids = set(
            r[0] for r in conn.execute("SELECT id FROM collections").fetchall()
        )

    stats = {
        "res_insert": 0, "res_update": 0,
        "content_new": 0, "content_tagline": 0,
        "acc_source": 0, "acc_short": 0, "acc_password": 0,
        "metrics_new": 0, "metrics_rating": 0,
        "col_linked": 0, "col_skipped": 0,
        "warnings": [],
    }

    row_num = 1
    for row in rows:
        d = extract_row(row, header)
        if d is None:
            continue

        res_id = f"p{row_num:03d}"
        row_num += 1

        if DRY_RUN:
            continue

        rc = sync_resources(cursor, res_id, d)
        if rc == 1:
            stats["res_insert"] += 1
        else:
            stats["res_update"] += 1

        if has_content:
            rc, tag = sync_content(cursor, res_id, d)
            if rc == 1:
                stats["content_new"] += 1
            stats["content_tagline"] += tag

        if has_access:
            ac = sync_access(cursor, res_id, d)
            stats["acc_source"]   += ac["source"]
            stats["acc_short"]    += ac["short"]
            stats["acc_password"] += ac["password"]

        if has_metrics:
            rc, rat = sync_metrics(cursor, res_id, d)
            if rc == 1:
                stats["metrics_new"] += 1
            stats["metrics_rating"]  += rat

        if has_collection and d["collections"]:
            linked, skipped = sync_collections(cursor, res_id, d, existing_collection_ids)
            stats["col_linked"]  += linked
            stats["col_skipped"] += len(skipped)
            for cid in skipped:
                stats["warnings"].append(f"collection '{cid}' not found ({res_id})")

    if not DRY_RUN:
        conn.commit()
    print_report(stats, DRY_RUN)
    conn.close()

# ============================================================
# 8. 报告
# ============================================================

def print_report(stats, dry_run=False):
    print()
    if dry_run:
        total = sum(1 for s in [stats] if s)  # placeholder
        print("=" * 50)
        print("  DRY-RUN — 未修改数据库")
        print("=" * 50)
        return

    print("=" * 50)
    print("  BigPRC Sync Report v2.0")
    print("=" * 50)

    total = stats["res_insert"] + stats["res_update"]
    print(f"\n  Resources:  新增 {stats['res_insert']}  更新 {stats['res_update']}  总计 {total}")

    if stats["content_new"] or stats["content_tagline"]:
        print(f"  Content:    新增行 {stats['content_new']}  tagline {stats['content_tagline']}")

    if stats["acc_source"] or stats["acc_short"] or stats["acc_password"]:
        print(f"  Access:     source {stats['acc_source']}  short {stats['acc_short']}  password {stats['acc_password']}")

    if stats["metrics_new"] or stats["metrics_rating"]:
        print(f"  Metrics:    新增行 {stats['metrics_new']}  rating {stats['metrics_rating']}")

    if stats["col_linked"] or stats["col_skipped"]:
        print(f"  Collections: linked {stats['col_linked']}  skipped {stats['col_skipped']}")

    if stats["warnings"]:
        print(f"\n  ⚠ Warnings ({len(stats['warnings'])}):")
        for w in stats["warnings"][:10]:
            print(f"    {w}")
        if len(stats["warnings"]) > 10:
            print(f"    ... +{len(stats['warnings']) - 10} more")

    print(f"\n  ✅ 同步完成")
    print()

# ============================================================
if __name__ == "__main__":
    main()

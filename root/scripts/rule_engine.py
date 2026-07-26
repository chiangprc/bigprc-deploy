#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BigPRC Rule Engine — Python 规则解析 + SQL 查询引擎 (Phase 5.3A)

将 collections.rule_json 转换为 SQL WHERE 子句，执行资源匹配。
支持 --dry-run 调试单个专题。

用法:
  python3 rule_engine.py --dry-run bbc-nature    # 单专题调试
  python3 rule_engine.py --verify                # 全量双写验证
"""

import json
import sqlite3
import os
import sys
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
DB_FILE = os.getenv("DB_FILE")

if not DB_FILE:
    print("❌ DB_FILE not set")
    sys.exit(1)

SUPPORTED_RULE_VERSION = 1

# ============================================================
# Rule Result
# ============================================================

class MatchResult:
    """单条规则匹配结果."""
    def __init__(self, collection_id, resource_ids, rule_version, warnings=None):
        self.collection_id = collection_id
        self.resource_ids = resource_ids      # list[str]
        self.count = len(resource_ids)
        self.rule_version = rule_version
        self.warnings = warnings or []

    def __repr__(self):
        return f"MatchResult({self.collection_id}, count={self.count}, v{self.rule_version})"

    def to_dict(self):
        return {
            "collection_id": self.collection_id,
            "count": self.count,
            "resource_ids": self.resource_ids[:20],
            "rule_version": self.rule_version,
            "warnings": self.warnings,
        }

# ============================================================
# Rule Parser
# ============================================================

def parse_rule(rule_json: dict):
    """将 rule_json 转换为 (WHERE子句, 参数列表, warnings列表).

    支持的字段:
      tags:         list[str] — AND 逻辑
      tags_or:      list[str] — OR 逻辑
      cats:         list[str] — category 筛选
      exclude_tags: list[str] — NOT EXISTS 排除逻辑
      min_resources: int       — 不进入 SQL, 由调用方判断
      version:      int        — 规则版本号 (不匹配时警告)

    Phase 6 预留 (静默跳过):
      platform, rating_min, language
    """
    conditions = []
    params = []
    warnings = []

    # version check
    rule_version = rule_json.get("version", 1)
    if rule_version != SUPPORTED_RULE_VERSION:
        warnings.append(
            f"rule_version={rule_version} != supported={SUPPORTED_RULE_VERSION}"
        )

    # AND tags
    for tag in rule_json.get("tags", []):
        conditions.append(
            "EXISTS (SELECT 1 FROM resource_tags rt "
            "JOIN tags t ON rt.tag_id=t.id "
            "WHERE rt.resource_id=r.res_id AND t.name=?)")
        params.append(tag)

    # OR tags
    tags_or = rule_json.get("tags_or")
    if tags_or:
        or_parts = []
        for tag in tags_or:
            or_parts.append(
                "EXISTS (SELECT 1 FROM resource_tags rt "
                "JOIN tags t ON rt.tag_id=t.id "
                "WHERE rt.resource_id=r.res_id AND t.name=?)")
            params.append(tag)
        conditions.append("(" + " OR ".join(or_parts) + ")")

    # exclude tags
    for tag in rule_json.get("exclude_tags", []):
        conditions.append(
            "NOT EXISTS (SELECT 1 FROM resource_tags rt "
            "JOIN tags t ON rt.tag_id=t.id "
            "WHERE rt.resource_id=r.res_id AND t.name=?)")
        params.append(tag)

    # category filter
    cats = rule_json.get("cats")
    if cats:
        conditions.append(
            "r.category IN ({})".format(",".join("?" * len(cats))))
        params.extend(cats)

    # Phase 6 reserved fields — skip silently
    for reserved in ("platform", "rating_min", "language"):
        if reserved in rule_json:
            warnings.append(f"reserved field '{reserved}' ignored (Phase 6)")

    where = " AND ".join(conditions) if conditions else "1=1"
    return where, params, warnings


# ============================================================
# Match Engine
# ============================================================

def match_collection(cursor, rule_json: dict, collection_id: str = None) -> MatchResult:
    """执行一条规则的匹配查询, 返回 MatchResult."""
    where, params, warnings = parse_rule(rule_json)
    min_resources = rule_json.get("min_resources", 3)
    rule_version = rule_json.get("version", 1)

    query = f"SELECT r.res_id FROM resources r WHERE {where}"
    rows = cursor.execute(query, params).fetchall()
    ids = [r[0] for r in rows]

    if len(ids) < min_resources:
        warnings.append(
            f"matched {len(ids)} resources < min_resources={min_resources}")

    return MatchResult(
        collection_id=collection_id or "unknown",
        resource_ids=ids,
        rule_version=rule_version,
        warnings=warnings,
    )


def match_all(cursor) -> dict:
    """读取 collections 表中所有 published 专题的 rule_json, 逐条匹配.

    Returns: {collection_id: MatchResult}
    """
    results = {}
    rows = cursor.execute(
        "SELECT id, rule_json FROM collections "
        "WHERE status='published' AND rule_json IS NOT NULL"
    ).fetchall()
    for cid, rule_raw in rows:
        if not rule_raw:
            continue
        try:
            rule = json.loads(rule_raw)
        except json.JSONDecodeError:
            results[cid] = MatchResult(cid, [], 0,
                                        [f"invalid JSON: {rule_raw[:50]}"])
            continue
        results[cid] = match_collection(cursor, rule, collection_id=cid)
    return results


# ============================================================
# Diff Engine (Set-level)
# ============================================================

def diff_collection(cursor, collection_id: str):
    """对比 DEFS 写入的 resource_collections 与 Rule Engine 结果.

    Returns: dict with missing, extra, exact, warnings
    """
    engine = match_all(cursor).get(collection_id)
    if not engine:
        return {"error": f"no rule_json for {collection_id}"}

    engine_ids = set(engine.resource_ids)

    db_ids = set(r[0] for r in cursor.execute(
        "SELECT resource_id FROM resource_collections WHERE collection_id=?",
        (collection_id,)))

    return {
        "collection_id": collection_id,
        "engine_count": len(engine_ids),
        "db_count": len(db_ids),
        "exact": sorted(engine_ids & db_ids),
        "missing": sorted(engine_ids - db_ids),   # engine found, DB missing
        "extra": sorted(db_ids - engine_ids),     # DB has, engine didn't find
        "warnings": engine.warnings,
    }


# ============================================================
# CLI
# ============================================================

def main():
    if "--verify" in sys.argv:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        results = match_all(cursor)
        all_ok = True
        for cid, result in results.items():
            diff = diff_collection(cursor, cid)
            status = "OK" if not diff.get("missing") and not diff.get("extra") else "DIFF"
            if status != "OK":
                all_ok = False
            print(f"  {status:4s} {cid:30s} engine={diff['engine_count']:4d}  "
                  f"db={diff['db_count']:4d}  "
                  f"missing={len(diff['missing'])} extra={len(diff['extra'])}")
            if diff.get("warnings"):
                for w in diff["warnings"]:
                    print(f"          ⚠️  {w}")
        conn.close()
        print(f"\n{'✅ All OK' if all_ok else '❌ Some DIFFs found — review above'}")
        return

    if "--dry-run" in sys.argv:
        idx = sys.argv.index("--dry-run")
        if idx + 1 >= len(sys.argv):
            print("Usage: python3 rule_engine.py --dry-run <collection_id>")
            sys.exit(1)
        cid = sys.argv[idx + 1]
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT id, title, rule_json FROM collections WHERE id=?",
            (cid,)).fetchone()
        if not row:
            print(f"❌ Collection '{cid}' not found")
            sys.exit(1)
        rule = json.loads(row[2]) if row[2] else {}
        result = match_collection(cursor, rule, collection_id=cid)
        diff = diff_collection(cursor, cid)
        print(f"Collection: {row[0]}  {row[1]}")
        print(f"Rule: {json.dumps(rule, ensure_ascii=False)}")
        print(f"Engine matched: {result.count} resources")
        print(f"DB resource_collections: {diff.get('db_count', '?')}")
        if result.warnings:
            for w in result.warnings:
                print(f"  ⚠️  {w}")
        if diff.get("missing"):
            print(f"  Missing from DB ({len(diff['missing'])}): {diff['missing'][:10]}")
        if diff.get("extra"):
            print(f"  Extra in DB ({len(diff['extra'])}): {diff['extra'][:10]}")
        if not diff.get("missing") and not diff.get("extra"):
            print("✅ Engine ↔ DB: exact match")
        conn.close()
        return

    print("Usage:")
    print("  python3 rule_engine.py --verify               # Verify all collections")
    print("  python3 rule_engine.py --dry-run <collection>  # Debug single collection")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
BigPRC Collection Health Check (Phase 5.4)

扫描专题体系，找出风险项：空专题、过少、规则失效、高度重叠。

用法:
  python3 collection_health.py              # 终端报告
  python3 collection_health.py --json       # JSON 输出
"""

import os, sys, json, sqlite3
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
DB_FILE = os.getenv("DB_FILE") or "/root/scripts/database.db"


def check_empty(cursor):
    """空专题: resource_collections 中无关联."""
    issues = []
    for row in cursor.execute("""
        SELECT c.id, c.title FROM collections c
        WHERE c.status='published'
        AND c.id NOT IN (SELECT DISTINCT collection_id FROM resource_collections)
    """).fetchall():
        issues.append({"type": "EMPTY", "id": row[0], "title": row[1],
                       "detail": "No resources linked", "severity": "HIGH"})
    return issues


def check_thin(cursor, threshold=3):
    """资源过少专题."""
    issues = []
    for row in cursor.execute("""
        SELECT c.id, c.title, COUNT(rc.resource_id) as cnt
        FROM collections c
        LEFT JOIN resource_collections rc ON c.id = rc.collection_id
        WHERE c.status='published' AND c.auto_generated = 1
        GROUP BY c.id HAVING cnt < ?
    """, (threshold,)).fetchall():
        issues.append({"type": "THIN", "id": row[0], "title": row[1],
                       "detail": f"Only {row[2]} resources (threshold={threshold})",
                       "severity": "MEDIUM"})
    return issues


def check_rule_dead(cursor):
    """规则失效: rule_json 存在但 Rule Engine 匹配为 0."""
    from rule_engine import match_collection

    issues = []
    for row in cursor.execute(
        "SELECT id, title, rule_json FROM collections WHERE status='published' AND rule_json IS NOT NULL"
    ).fetchall():
        try:
            rule = json.loads(row[2])
        except (json.JSONDecodeError, TypeError):
            issues.append({"type": "BROKEN_RULE", "id": row[0], "title": row[1],
                           "detail": "rule_json is invalid JSON", "severity": "HIGH"})
            continue
        result = match_collection(cursor, rule, collection_id=row[0])
        if result.count == 0:
            issues.append({"type": "DEAD_RULE", "id": row[0], "title": row[1],
                           "detail": "Rule Engine matched 0 resources", "severity": "HIGH"})
    return issues


def check_overlap(cursor, threshold_pct=60):
    """高度重叠: 两个专题共享 >60% 资源."""
    issues = []
    colls = cursor.execute(
        "SELECT id, title FROM collections WHERE status='published'"
    ).fetchall()

    for i, (cid_a, title_a) in enumerate(colls):
        ids_a = set(r[0] for r in cursor.execute(
            "SELECT resource_id FROM resource_collections WHERE collection_id=?", (cid_a,)).fetchall())
        if len(ids_a) < 5:
            continue
        for cid_b, title_b in colls[i+1:]:
            ids_b = set(r[0] for r in cursor.execute(
                "SELECT resource_id FROM resource_collections WHERE collection_id=?", (cid_b,)).fetchall())
            if len(ids_b) < 5:
                continue
            intersection = len(ids_a & ids_b)
            overlap_pct = round(100 * intersection / min(len(ids_a), len(ids_b)), 1)
            if overlap_pct >= threshold_pct:
                issues.append({
                    "type": "OVERLAP",
                    "collections": [{"id": cid_a, "title": title_a, "count": len(ids_a)},
                                    {"id": cid_b, "title": title_b, "count": len(ids_b)}],
                    "overlap_pct": overlap_pct,
                    "shared_resources": intersection,
                    "severity": "MEDIUM",
                })
    return issues


def print_terminal(all_issues):
    print()
    print("=" * 60)
    print("  Collection Health Check")
    print("=" * 60)

    by_severity = {"HIGH": [], "MEDIUM": [], "LOW": []}
    for item in all_issues:
        by_severity[item.get("severity", "LOW")].append(item)

    for sev in ["HIGH", "MEDIUM", "LOW"]:
        items = by_severity[sev]
        if not items:
            continue
        print(f"\n── {sev} ({len(items)}) ──")
        for item in items:
            t = item["type"]
            if t == "EMPTY":
                print(f"  🫙 {item['id']}: {item['title']} — {item['detail']}")
            elif t == "THIN":
                print(f"  📉 {item['id']}: {item['title']} — {item['detail']}")
            elif t in ("DEAD_RULE", "BROKEN_RULE"):
                print(f"  💀 {item['id']}: {item['title']} — {item['detail']}")
            elif t == "OVERLAP":
                a = item["collections"][0]
                b = item["collections"][1]
                print(f"  🔀 {a['title']} ({a['count']}) ↔ {b['title']} ({b['count']}) — {item['overlap_pct']}% overlap ({item['shared_resources']} shared)")

    total = len(all_issues)
    if total == 0:
        print("\n  ✅ No issues found. All collections healthy.")
    else:
        print(f"\n  Total issues: {total}")
    print()


def print_json(all_issues):
    print(json.dumps({"issues": all_issues, "total": len(all_issues)}, ensure_ascii=False))


def main():
    json_out = "--json" in sys.argv
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    issues = (
        check_empty(cursor) +
        check_thin(cursor) +
        check_rule_dead(cursor) +
        check_overlap(cursor)
    )
    conn.close()

    if json_out:
        print_json(issues)
    else:
        print_terminal(issues)


if __name__ == "__main__":
    main()

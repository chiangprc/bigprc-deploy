#!/usr/bin/env python3
"""
BigPRC Collection Quality Report (Phase 5.4)

读取数据库，输出每个专题的覆盖分析、独占/重复资源、质量评级。
纯只读分析，不修改数据库。

用法:
  python3 collection_quality_report.py              # 终端报告
  python3 collection_quality_report.py --json        # JSON 输出
  python3 collection_quality_report.py --json -o report.json
"""

import os, sys, json, sqlite3
from collections import defaultdict
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
DB_FILE = os.getenv("DB_FILE") or "/root/scripts/database.db"


def get_quality_report(cursor):
    total_resources = cursor.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    colls = cursor.execute(
        "SELECT id, title, is_featured, auto_generated, rule_json FROM collections WHERE status='published' ORDER BY title"
    ).fetchall()

    results = []
    for cid, ctitle, featured, auto_gen, rule_raw in colls:
        # Resource count
        cnt = cursor.execute(
            "SELECT COUNT(*) FROM resource_collections WHERE collection_id=?", (cid,)).fetchone()[0]
        if cnt == 0:
            results.append({
                "id": cid, "title": ctitle, "resource_count": 0,
                "coverage_pct": 0, "exclusive_count": 0, "shared_count": 0,
                "avg_tags": 0, "quality": "EMPTY", "featured": bool(featured),
                "auto_generated": bool(auto_gen), "rule_json": rule_raw,
            })
            continue

        # Coverage
        coverage_pct = round(100 * cnt / total_resources, 2)

        # Exclusive vs shared (资源是否也属于其他专题)
        shared = cursor.execute("""
            SELECT COUNT(DISTINCT rc1.resource_id)
            FROM resource_collections rc1
            JOIN resource_collections rc2 ON rc1.resource_id = rc2.resource_id AND rc2.collection_id != rc1.collection_id
            WHERE rc1.collection_id = ?
        """, (cid,)).fetchone()[0]
        exclusive = cnt - shared

        # Average tag count per resource
        avg_tags = cursor.execute("""
            SELECT AVG(cnt) FROM (
                SELECT COUNT(*) as cnt FROM resource_tags
                WHERE resource_id IN (SELECT resource_id FROM resource_collections WHERE collection_id=?)
                GROUP BY resource_id
            )
        """, (cid,)).fetchone()[0]
        avg_tags = round(avg_tags, 1) if avg_tags else 0

        # Quality assessment
        if cnt >= 100 and exclusive > cnt * 0.5:
            quality = "CORE"
        elif cnt >= 20:
            quality = "SOLID"
        elif cnt >= 5:
            quality = "NICHE"
        else:
            quality = "THIN"

        results.append({
            "id": cid, "title": ctitle, "resource_count": cnt,
            "coverage_pct": coverage_pct, "exclusive_count": exclusive,
            "shared_count": shared, "avg_tags": avg_tags,
            "quality": quality,
            "featured": bool(featured), "auto_generated": bool(auto_gen),
            "rule_json": rule_raw,
        })

    return {
        "total_resources": total_resources,
        "total_collections": len(results),
        "collections": sorted(results, key=lambda x: -x["resource_count"]),
    }


def print_terminal(report):
    print()
    print("=" * 80)
    print(f"  Collection Quality Report")
    print(f"  {report['total_resources']} resources · {report['total_collections']} collections")
    print("=" * 80)
    print()
    print(f"  {'Title':28s} {'Resources':>9s} {'Exclusive':>9s} {'Shared':>6s} {'Cov%':>5s} {'Tags':>5s} {'Quality'}")
    print("  " + "─" * 72)

    for c in report["collections"]:
        tag = "[*]" if c["featured"] else "   "
        print(f"  {tag} {c['title']:26s} {c['resource_count']:>9d} {c['exclusive_count']:>9d} {c['shared_count']:>6d} {c['coverage_pct']:>5.1f} {c['avg_tags']:>5.1f} {c['quality']:8s}")

    print()
    print(f"  Quality summary:")
    for q in ["CORE", "SOLID", "NICHE", "THIN", "EMPTY"]:
        count = len([c for c in report["collections"] if c["quality"] == q])
        if count:
            print(f"    {q:8s}: {count}")
    print()


def print_json(report):
    print(json.dumps(report, ensure_ascii=False))


def main():
    json_out = "--json" in sys.argv
    out_file = None
    for i, a in enumerate(sys.argv):
        if a == "-o" and i+1 < len(sys.argv):
            out_file = sys.argv[i+1]

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    report = get_quality_report(cursor)
    conn.close()

    if json_out:
        output = json.dumps(report, ensure_ascii=False)
        if out_file:
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"✅ Written to {out_file}")
        else:
            print(output)
    else:
        print_terminal(report)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
BigPRC Dashboard Data Exporter (Phase 6.0)

Combines quality report + health check + strategy report + review data
into static JSON files for the editorial dashboard.

Output:
  /var/www/site/web/admin/data/dashboard.json
  /var/www/site/web/admin/data/collections.json
"""

import os, sys, json, sqlite3
from collections import defaultdict
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
DB_FILE = os.getenv("DB_FILE") or "/root/scripts/database.db"
OUT_DIR = "/var/www/site/web/admin/data"
REVIEW_DATA = os.path.join(OUT_DIR, "review-data.json")


def build_dashboard(cursor):
    """总览数据: 概要卡片 + 健康 + 最新发现."""
    # Collection counts
    total = cursor.execute("SELECT COUNT(*) FROM collections WHERE status='published'").fetchone()[0]
    featured = cursor.execute("SELECT COUNT(*) FROM collections WHERE status='published' AND is_featured=1").fetchone()[0]
    auto_gen = cursor.execute("SELECT COUNT(*) FROM collections WHERE status='published' AND auto_generated=1").fetchone()[0]

    # Quality tiers
    core_count = 0
    solid_count = 0
    niche_count = 0
    for row in cursor.execute("""
        SELECT c.id, COUNT(rc.resource_id) as cnt FROM collections c
        LEFT JOIN resource_collections rc ON c.id = rc.collection_id
        WHERE c.status='published' GROUP BY c.id
    """).fetchall():
        cnt = row[1]
        if cnt >= 100:
            core_count += 1
        elif cnt >= 20:
            solid_count += 1
        elif cnt >= 5:
            niche_count += 1

    # Health summary
    from collection_health import check_empty, check_thin, check_rule_dead, check_overlap
    health_issues = (
        check_empty(cursor) + check_thin(cursor) + check_rule_dead(cursor) + check_overlap(cursor)
    )
    health_counts = defaultdict(int)
    for item in health_issues:
        health_counts[item["severity"]] += 1

    # Review pending counts
    review_new = 0
    review_expand = 0
    review_keep = 0
    recent_findings = []
    if os.path.exists(REVIEW_DATA):
        with open(REVIEW_DATA, "r", encoding="utf-8") as f:
            review = json.load(f)
        for g in review.get("groups", []):
            a = g.get("action", "")
            if a == "NEW_COLLECTION":
                review_new += 1
            elif a == "EXPAND_RULE":
                review_expand += 1
            elif a == "KEEP":
                review_keep += 1
            if a in ("NEW_COLLECTION", "EXPAND_RULE"):
                recent_findings.append({
                    "candidate_tags": g.get("candidate_tags", []),
                    "match_count": g.get("match_count", 0),
                    "action": a,
                    "action_label": g.get("action_label", a),
                    "best_match": g.get("best_match"),
                })

    return {
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "summary": {
            "total_collections": total,
            "featured": featured,
            "auto_generated": auto_gen,
            "core": core_count,
            "solid": solid_count,
            "niche": niche_count,
        },
        "health": {
            "total_issues": len(health_issues),
            "high": health_counts.get("HIGH", 0),
            "medium": health_counts.get("MEDIUM", 0),
            "stable": total - health_counts.get("HIGH", 0) - health_counts.get("MEDIUM", 0),
        },
        "review_pending": {
            "new_collection": review_new,
            "expand_rule": review_expand,
            "keep": review_keep,
        },
        "recent_findings": recent_findings[:10],
    }


def build_collections(cursor):
    """专题列表: 质量 + 健康."""
    from rule_engine import match_collection

    rows = cursor.execute("""
        SELECT c.id, c.title, c.rule_json, c.is_featured, c.auto_generated
        FROM collections c WHERE c.status='published' ORDER BY c.title
    """).fetchall()

    result = []
    for cid, ctitle, rule_raw, featured, auto_gen in rows:
        cnt = cursor.execute(
            "SELECT COUNT(*) FROM resource_collections WHERE collection_id=?", (cid,)).fetchone()[0]
        if cnt >= 100:
            quality = "CORE"
        elif cnt >= 20:
            quality = "SOLID"
        elif cnt >= 5:
            quality = "NICHE"
        else:
            quality = "THIN" if cnt > 0 else "EMPTY"

        # Health quick check
        health = "stable"
        if cnt == 0:
            health = "empty"
        elif rule_raw:
            try:
                rule = json.loads(rule_raw)
                m = match_collection(cursor, rule, collection_id=cid)
                delta = round(100 * abs(m.count - cnt) / max(cnt, 1), 1)
                if delta >= 20:
                    health = "unstable"
                elif delta >= 5:
                    health = "warning"
            except (json.JSONDecodeError, TypeError):
                health = "broken"

        result.append({
            "id": cid, "title": ctitle,
            "resource_count": cnt, "quality": quality, "health": health,
            "featured": bool(featured), "auto_generated": bool(auto_gen),
            "rule_json": rule_raw,
        })

    return sorted(result, key=lambda x: -x["resource_count"])


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    dashboard = build_dashboard(cursor)
    collections = build_collections(cursor)
    conn.close()

    for name, data in [("dashboard.json", dashboard), ("collections.json", collections)]:
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"✅ {path} ({os.path.getsize(path)} bytes)")

    print(f"\n   Open: https://www.bigprc.com/admin/dashboard.html")


if __name__ == "__main__":
    main()

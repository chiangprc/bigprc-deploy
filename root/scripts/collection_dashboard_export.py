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


def build_collection_details(cursor):
    """每个专题的深度分析: rule engine summary, top tags, shared collections, samples."""
    from rule_engine import match_collection

    colls = cursor.execute(
        "SELECT id, title, rule_json, is_featured, auto_generated FROM collections WHERE status='published' ORDER BY title"
    ).fetchall()
    result = []
    total_resources = cursor.execute("SELECT COUNT(*) FROM resources").fetchone()[0]

    for cid, ctitle, rule_raw, featured, auto_gen in colls:
        cnt = cursor.execute(
            "SELECT COUNT(*) FROM resource_collections WHERE collection_id=?", (cid,)).fetchone()[0]
        if cnt >= 100: quality = "CORE"
        elif cnt >= 20: quality = "SOLID"
        elif cnt >= 5: quality = "NICHE"
        else: quality = "THIN" if cnt > 0 else "EMPTY"

        # Health
        health = "stable"
        engine_match = cnt
        engine_delta_pct = 0
        engine_summary = {}
        if rule_raw:
            try:
                rule = json.loads(rule_raw)
                m = match_collection(cursor, rule, collection_id=cid)
                engine_match = m.count
                engine_delta_pct = round(100 * abs(m.count - cnt) / max(cnt, 1), 1)
                if engine_delta_pct >= 20: health = "unstable"
                elif engine_delta_pct >= 5: health = "warning"
                # Rule engine summary: per-condition hit counts
                engine_summary = _engine_summary(cursor, rule, m.resource_ids)
            except (json.JSONDecodeError, TypeError):
                health = "broken"

        # Exclusive / shared
        shared = cursor.execute("""
            SELECT COUNT(DISTINCT rc1.resource_id)
            FROM resource_collections rc1
            JOIN resource_collections rc2 ON rc1.resource_id = rc2.resource_id AND rc2.collection_id != rc1.collection_id
            WHERE rc1.collection_id = ?
        """, (cid,)).fetchone()[0]
        exclusive = cnt - shared
        exclusive_pct = round(100 * exclusive / cnt) if cnt > 0 else 0

        # Top Tags
        top_tags = []
        if cnt > 0:
            for row in cursor.execute("""
                SELECT t.name, COUNT(*) as n FROM resource_tags rt
                JOIN tags t ON rt.tag_id = t.id
                WHERE rt.resource_id IN (SELECT resource_id FROM resource_collections WHERE collection_id=?)
                GROUP BY t.name ORDER BY n DESC LIMIT 12
            """, (cid,)).fetchall():
                top_tags.append({"name": row[0], "count": row[1]})

        # Shared collections
        shared_colls = []
        if cnt > 0:
            for row in cursor.execute("""
                SELECT c2.id, c2.title, COUNT(DISTINCT rc1.resource_id) as shared
                FROM resource_collections rc1
                JOIN resource_collections rc2 ON rc1.resource_id = rc2.resource_id AND rc2.collection_id != rc1.collection_id
                JOIN collections c2 ON rc2.collection_id = c2.id
                WHERE rc1.collection_id = ?
                GROUP BY c2.id ORDER BY shared DESC LIMIT 5
            """, (cid,)).fetchall():
                shared_colls.append({
                    "id": row[0], "title": row[1],
                    "shared": row[2],
                    "shared_pct": round(100 * row[2] / cnt, 1),
                })

        # Samples (first 50)
        samples = []
        if cnt > 0:
            for row in cursor.execute("""
                SELECT r.res_id, r.title, r.category FROM resources r
                JOIN resource_collections rc ON r.res_id = rc.resource_id
                WHERE rc.collection_id = ? ORDER BY rc.score DESC LIMIT 50
            """, (cid,)).fetchall():
                samples.append({"id": row[0], "title": row[1], "category": row[2]})

        # Coverage
        coverage_pct = round(100 * cnt / total_resources, 2)

        result.append({
            "id": cid, "title": ctitle, "quality": quality, "health": health,
            "featured": bool(featured), "auto_generated": bool(auto_gen),
            "resource_count": cnt,
            "exclusive_count": exclusive, "shared_count": shared,
            "exclusive_pct": exclusive_pct, "coverage_pct": coverage_pct,
            "rule_json": rule_raw,
            "engine_match": engine_match, "engine_delta_pct": engine_delta_pct,
            "engine_summary": engine_summary,
            "top_tags": top_tags,
            "shared_collections": shared_colls,
            "samples": samples,
            "editor_notes": None,
            "recent_changes": None,
            "ai_suggestion": None,
        })

    return sorted(result, key=lambda x: -x["resource_count"])


def _engine_summary(cursor, rule, matched_ids):
    """Per-condition hit count breakdown for Rule Engine debugging."""
    summary = {"total_matched": len(matched_ids)}
    if rule.get("tags"):
        for tag in rule["tags"]:
            cnt = cursor.execute("""
                SELECT COUNT(DISTINCT rt.resource_id) FROM resource_tags rt
                JOIN tags t ON rt.tag_id = t.id WHERE t.name = ?
            """, (tag,)).fetchone()[0]
            summary[f"tag:{tag}"] = cnt
    if rule.get("tags_or"):
        for tag in rule["tags_or"]:
            cnt = cursor.execute("""
                SELECT COUNT(DISTINCT rt.resource_id) FROM resource_tags rt
                JOIN tags t ON rt.tag_id = t.id WHERE t.name = ?
            """, (tag,)).fetchone()[0]
            summary[f"tag_or:{tag}"] = cnt
    if rule.get("cats"):
        for cat in rule["cats"]:
            cnt = cursor.execute(
                "SELECT COUNT(*) FROM resources WHERE category = ?", (cat,)).fetchone()[0]
            summary[f"cat:{cat}"] = cnt
    return summary


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    dashboard = build_dashboard(cursor)
    collections = build_collections(cursor)
    details = build_collection_details(cursor)
    conn.close()

    for name, data in [("dashboard.json", dashboard), ("collections.json", collections),
                        ("collection-details.json", details)]:
        path = os.path.join(OUT_DIR, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"✅ {path} ({os.path.getsize(path)} bytes)")

    print(f"\n   Open: https://www.bigprc.com/admin/dashboard.html")


if __name__ == "__main__":
    main()

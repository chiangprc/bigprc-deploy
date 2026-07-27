#!/usr/bin/env python3
"""
BigPRC Collection Strategy Report (Phase 5.5)

综合分析专题体系，输出首页排序、关系分析、规则稳定性。
纯只读，不修改数据库。

用法:
  python3 collection_strategy_report.py              # 终端报告
  python3 collection_strategy_report.py --json       # JSON 输出
"""

import os, sys, json, sqlite3
from collections import defaultdict
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
DB_FILE = os.getenv("DB_FILE") or "/root/scripts/database.db"

# ============================================================
# Section 1 — Homepage Ranking
# ============================================================

def score_collection(cursor, cid, ctitle, featured, auto_gen, cnt, rule_raw):
    """综合评分: 资源量(40%) + 独占度(30%) + 精选(20%) + 人工(10%)."""
    if cnt == 0:
        return {"id": cid, "title": ctitle, "score": 0, "detail": "empty"}

    # Resource count score (0-40)
    total = cursor.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    size_score = min(40, round(40 * cnt / max(cnt for _, _, _, _, _, c, _ in
        [(None, None, None, None, None, c2, None) for c2 in
         [cursor.execute("SELECT MAX(cnt) FROM (SELECT COUNT(*) as cnt FROM resource_collections GROUP BY collection_id)").fetchone()[0]]])))

    # Exclusive ratio (0-30)
    shared = cursor.execute("""
        SELECT COUNT(DISTINCT rc1.resource_id)
        FROM resource_collections rc1
        JOIN resource_collections rc2 ON rc1.resource_id = rc2.resource_id AND rc2.collection_id != rc1.collection_id
        WHERE rc1.collection_id = ?
    """, (cid,)).fetchone()[0]
    exclusive = cnt - shared
    excl_ratio = exclusive / cnt if cnt > 0 else 0
    excl_score = round(30 * excl_ratio)

    # Featured (0-20)
    feat_score = 20 if featured else 0

    # Human-curated bonus (0-10)
    human_score = 10 if not auto_gen else 0

    score = size_score + excl_score + feat_score + human_score

    return {
        "id": cid, "title": ctitle,
        "score": score,
        "score_breakdown": {
            "size": size_score, "exclusive": excl_score,
            "featured": feat_score, "human": human_score,
        },
        "metrics": {
            "resource_count": cnt, "exclusive_count": exclusive,
            "exclusive_ratio": round(excl_ratio * 100),
        },
    }


def homepage_ranking(cursor):
    rows = cursor.execute(
        "SELECT id, title, is_featured, auto_generated, rule_json FROM collections WHERE status='published'"
    ).fetchall()
    scores = []
    for cid, ctitle, feat, auto_gen, rule_raw in rows:
        cnt = cursor.execute(
            "SELECT COUNT(*) FROM resource_collections WHERE collection_id=?", (cid,)).fetchone()[0]
        if cnt == 0:
            continue
        scores.append(score_collection(cursor, cid, ctitle, feat, auto_gen, cnt, rule_raw))
    return sorted(scores, key=lambda x: -x["score"])


# ============================================================
# Section 2 — Relationship Analysis
# ============================================================

def relationship_analysis(cursor):
    """发现父子关系候选 + 合并候选."""
    colls = cursor.execute(
        "SELECT id, title FROM collections WHERE status='published'").fetchall()
    coll_res = {}
    for cid, _ in colls:
        ids = set(r[0] for r in cursor.execute(
            "SELECT resource_id FROM resource_collections WHERE collection_id=?", (cid,)).fetchall())
        if ids:
            coll_res[cid] = ids

    parents = []
    merges = []

    items = list(coll_res.items())
    for i, (cid_a, ids_a) in enumerate(items):
        for cid_b, ids_b in items[i+1:]:
            if len(ids_a) >= 10 and len(ids_b) >= 3:
                # Parent-child: A contains >80% of B
                containment = len(ids_a & ids_b) / max(len(ids_b), 1)
                if containment >= 0.8 and len(ids_a) >= 2 * len(ids_b):
                    title_a = dict(colls)[cid_a]
                    title_b = dict(colls)[cid_b]
                    parents.append({
                        "parent": {"id": cid_a, "title": title_a, "count": len(ids_a)},
                        "child": {"id": cid_b, "title": title_b, "count": len(ids_b)},
                        "containment_pct": round(100 * containment),
                    })

            # Merge: >60% bidirectional overlap
            if len(ids_a) >= 5 and len(ids_b) >= 5:
                overlap_pct = 100 * len(ids_a & ids_b) / min(len(ids_a), len(ids_b))
                if overlap_pct >= 60:
                    title_a = dict(colls)[cid_a]
                    title_b = dict(colls)[cid_b]
                    merges.append({
                        "collections": [
                            {"id": cid_a, "title": title_a, "count": len(ids_a)},
                            {"id": cid_b, "title": title_b, "count": len(ids_b)},
                        ],
                        "overlap_pct": round(overlap_pct),
                        "shared": len(ids_a & ids_b),
                    })

    return {"parents": parents, "merges": merges}


# ============================================================
# Section 3 — Rule Stability
# ============================================================

def rule_stability(cursor):
    """比较 rule_json 匹配数 vs resource_collections 实际数."""
    from rule_engine import match_collection

    results = []
    for row in cursor.execute(
        "SELECT id, title, rule_json FROM collections WHERE status='published' AND rule_json IS NOT NULL"
    ).fetchall():
        cid, ctitle, rule_raw = row
        try:
            rule = json.loads(rule_raw)
        except (json.JSONDecodeError, TypeError):
            results.append({"id": cid, "title": ctitle, "stability": "broken", "detail": "invalid JSON"})
            continue

        actual = cursor.execute(
            "SELECT COUNT(*) FROM resource_collections WHERE collection_id=?", (cid,)).fetchone()[0]
        match = match_collection(cursor, rule, collection_id=cid)
        engine = match.count

        if actual == 0:
            results.append({"id": cid, "title": ctitle, "stability": "empty", "detail": "0 resources"})
            continue

        delta_pct = round(100 * abs(engine - actual) / actual, 1)
        if delta_pct < 5:
            stability = "stable"
        elif delta_pct < 20:
            stability = "warning"
        else:
            stability = "unstable"

        results.append({
            "id": cid, "title": ctitle,
            "stability": stability,
            "actual_count": actual,
            "engine_match": engine,
            "delta_pct": delta_pct,
            "detail": f"DB={actual} Engine={engine} (Δ{delta_pct}%)",
        })

    return sorted(results, key=lambda x: {"stable": 0, "warning": 1, "unstable": 2, "empty": 3, "broken": 4}.get(x["stability"], 5))


# ============================================================
# Output
# ============================================================

def print_terminal(ranking, relations, stability):
    print()
    print("=" * 60)
    print("  Collection Strategy Report")
    print("=" * 60)

    # Ranking
    print(f"\n── 首页推荐 Top 10 ──")
    for i, r in enumerate(ranking[:10]):
        star = "⭐" if r["score"] >= 70 else "  "
        print(f"  {i+1:2d}. {star} {r['title']:28s} score={r['score']:3d}  "
              f"({r['metrics']['resource_count']}资源, {r['metrics']['exclusive_ratio']}%独占)")

    # Relationships
    print(f"\n── 父子关系候选 ({len(relations['parents'])} found) ──")
    for p in relations["parents"]:
        print(f"  {p['parent']['title']} ({p['parent']['count']})"
              f"  ↖ {p['child']['title']} ({p['child']['count']})"
              f"  ({p['containment_pct']}% contained)")

    print(f"\n── 疑似合并 ({len(relations['merges'])} found) ──")
    for m in relations["merges"]:
        a, b = m["collections"][0], m["collections"][1]
        print(f"  {a['title']} ({a['count']}) ↔ {b['title']} ({b['count']})"
              f"  ({m['overlap_pct']}% overlap, {m['shared']} shared)")

    # Stability
    print(f"\n── Rule 稳定性 ──")
    for r in stability:
        icon = {"stable":"🟢","warning":"🟡","unstable":"🔴","empty":"⚪","broken":"💀"}.get(r["stability"],"?")
        print(f"  {icon} {r['title']:28s} {r['detail']}")

    print()


def print_json(ranking, relations, stability):
    print(json.dumps({
        "homepage_ranking": ranking,
        "relationships": relations,
        "rule_stability": stability,
    }, ensure_ascii=False))


def main():
    json_out = "--json" in sys.argv
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    ranking = homepage_ranking(cursor)
    relations = relationship_analysis(cursor)
    stability = rule_stability(cursor)

    conn.close()

    if json_out:
        print_json(ranking, relations, stability)
    else:
        print_terminal(ranking, relations, stability)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BigPRC Collection Gap Analyzer — 专题覆盖差距分析 (Phase 5.3D)

职责: 读取 Discovery JSON, 通过 Rule Engine 重算覆盖, 输出差距报告。
边界: 只读分析。不修改 Rule, 不创建专题, 不写数据库。

算法:
  1. 读取 stdin/piped Discovery JSON (或 --input file)
  2. 对每个 Discovery Group, 调用 Rule Engine 逐专题计算覆盖
  3. 按覆盖度分类: KEEP / EXPAND_RULE / NEW_COLLECTION / MERGE_REVIEW
  4. 输出终端报告 + JSON

用法:
  python3 collection_discovery.py --scan --json | python3 collection_gap.py --analyze
  python3 collection_gap.py --analyze --input discovery.json
  python3 collection_gap.py --analyze --input discovery.json --json

Config: 读取 /root/scripts/.env (DB_FILE)
"""

import os
import sys
import json
import sqlite3
from collections import defaultdict
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
DB_FILE = os.getenv("DB_FILE")

if not DB_FILE:
    print("❌ DB_FILE not set in .env")
    print("   Add: DB_FILE=/root/scripts/database.db")
    sys.exit(1)

# ============================================================
# Core Logic
# ============================================================

def classify_action(covered_total, uncovered_total, best_match_count, second_best_count):
    """分类建议动作 (无硬编码阈值).

    KEEP:           全部资源被已有专题覆盖 (uncovered == 0)
    EXPAND_RULE:    存在 dominant best match (覆盖 >= 70%),
                    且 best 明显优于 second (best >= 2× second)
    MERGE_REVIEW:   多个专题覆盖相近 (best 和 second 差距 < 2×),
                    可能是专题边界模糊或规则重叠
    NEW_COLLECTION: 无 dominant best match (best < 70%),
                    这是真正的新专题机会
    """
    if uncovered_total == 0:
        return "KEEP"

    coverage_pct = best_match_count / (covered_total + uncovered_total) if (covered_total + uncovered_total) > 0 else 0

    # Dominant: >= 70% AND clearly ahead of second (>= 2x)
    if coverage_pct >= 0.7 and (second_best_count == 0 or best_match_count >= 2 * second_best_count):
        return "EXPAND_RULE"

    # Multiple contenders: best < 2× second
    if second_best_count > 0 and best_match_count < 2 * second_best_count:
        return "MERGE_REVIEW"

    return "NEW_COLLECTION"


def analyze_group(cursor, group):
    """分析一个 Discovery Group 的覆盖情况.

    使用 Rule Engine 逐专题重算覆盖 (不依赖 resource_collections 历史数据).
    """
    from rule_engine import match_collection

    resource_ids = set(group["resource_ids"])
    total = len(resource_ids)
    all_covered = set()

    # 获取所有 published collection 的 rule_json
    colls = cursor.execute(
        "SELECT id, title, rule_json FROM collections WHERE status='published' AND rule_json IS NOT NULL"
    ).fetchall()

    matches = []  # [{id, title, covered_count, overlap_pct}, ...]
    for cid, ctitle, rule_raw in colls:
        try:
            rule = json.loads(rule_raw)
        except (json.JSONDecodeError, TypeError):
            continue
        result = match_collection(cursor, rule, collection_id=cid)
        matched_ids = set(result.resource_ids)
        overlap = resource_ids & matched_ids
        if overlap:
            matches.append({
                "id": cid,
                "title": ctitle,
                "covered_count": len(overlap),
                "overlap_pct": round(100 * len(overlap) / total, 1),
            })
            all_covered |= overlap

    matches.sort(key=lambda x: -x["covered_count"])
    best = matches[0] if matches else None
    second = matches[1] if len(matches) >= 2 else None
    uncovered = resource_ids - all_covered

    action = classify_action(
        covered_total=len(all_covered),
        uncovered_total=len(uncovered),
        best_match_count=best["covered_count"] if best else 0,
        second_best_count=second["covered_count"] if second else 0,
    )

    return {
        "candidate_tags": group["candidate_tags"],
        "match_count": total,
        "covered_count": len(all_covered),
        "uncovered_count": len(uncovered),
        "uncovered_ids": sorted(uncovered)[:20],
        "best_match": best,
        "all_matches": matches[:5],
        "action": action,
        "action_label": {
            "KEEP": "✅ 已全覆盖",
            "EXPAND_RULE": "🔧 建议完善规则",
            "MERGE_REVIEW": "🔀 多个专题重叠",
            "NEW_COLLECTION": "🆕 新专题候选",
        }.get(action, action),
    }


# ============================================================
# Output
# ============================================================

def print_terminal(results):
    print()
    print(f"{'Tag组':35s} {'发现':>4s} {'覆盖':>4s} {'未覆盖':>4s} {'动作':12s} {'最佳匹配专题'}")
    print("─" * 90)
    for r in results:
        tags_str = " ".join(r["candidate_tags"][:4])
        best_name = r["best_match"]["title"] if r["best_match"] else "—"
        print(f"{tags_str:35s} {r['match_count']:4d} {r['covered_count']:4d} {r['uncovered_count']:4d} {r['action_label']:12s} {best_name[:30]}")
    print()

    # Summary
    counts = defaultdict(int)
    for r in results:
        counts[r["action"]] += 1
    print(f"总计: {len(results)} 个发现组")
    for action, label in [("KEEP","已全覆盖"),("EXPAND_RULE","建议完善规则"),("MERGE_REVIEW","专题重叠"),("NEW_COLLECTION","新专题候选")]:
        if counts.get(action):
            print(f"  {label}: {counts[action]}")
    print()


def print_json(results):
    print(json.dumps({
        "analyzed_at": __import__("datetime").datetime.now().isoformat(),
        "total_groups": len(results),
        "summary": {k: len([r for r in results if r["action"] == k])
                     for k in ["KEEP","EXPAND_RULE","MERGE_REVIEW","NEW_COLLECTION"]},
        "groups": results,
    }, ensure_ascii=False))


# ============================================================
# CLI
# ============================================================

def main():
    analyze = "--analyze" in sys.argv
    json_out = "--json" in sys.argv
    input_file = None

    for i, a in enumerate(sys.argv):
        if a == "--input" and i+1 < len(sys.argv):
            input_file = sys.argv[i+1]

    if not analyze:
        print("Usage: python3 collection_gap.py --analyze [--input file.json] [--json]")
        print()
        print("  collection_discovery.py --scan --json | python3 collection_gap.py --analyze")
        print("  python3 collection_gap.py --analyze --input discovery.json")
        return

    # Read Discovery JSON
    if input_file:
        with open(input_file, "r", encoding="utf-8") as f:
            discovery = json.load(f)
    else:
        discovery = json.load(sys.stdin)

    groups = discovery.get("groups", [])
    if not groups:
        print("❌ No Discovery groups found in input")
        sys.exit(1)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    results = [analyze_group(cursor, g) for g in groups]

    conn.close()

    if json_out:
        print_json(results)
    else:
        print_terminal(results)


if __name__ == "__main__":
    main()

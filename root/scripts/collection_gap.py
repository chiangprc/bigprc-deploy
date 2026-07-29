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

def classify_action(covered_total, uncovered_total, best_match_count, second_best_count,
                    semantic_overlap=False):
    """分类建议动作 (无硬编码阈值).

    KEEP:           全部资源被已有专题覆盖 (uncovered == 0)
    EXPAND_RULE:    存在 dominant best match (覆盖 >= 60%),
                    或 best 的 rule tags 与 Discovery tags 语义重叠
    MERGE_REVIEW:   多个专题覆盖相近 (best 和 second 差距 < 2×),
                    可能是专题边界模糊或规则重叠
    NEW_COLLECTION: 无 dominant best match AND 无语义重叠,
                    这是真正的新专题机会

    semantic_overlap: 最佳匹配专题的 rule tags 与 Discovery 候选 tags
                      存在交集 → 应优先考虑扩展现有规则而非新建专题
    """
    total = covered_total + uncovered_total
    if total == 0:
        return "KEEP"
    if uncovered_total == 0:
        return "KEEP"

    coverage_pct = best_match_count / total

    # Dominant + semantic overlap: even lower coverage qualifies for EXPAND
    if semantic_overlap and coverage_pct >= 0.3:
        return "EXPAND_RULE"

    # Dominant: >= 60% AND clearly ahead of second (>= 2x)
    if coverage_pct >= 0.6 and (second_best_count == 0 or best_match_count >= 2 * second_best_count):
        return "EXPAND_RULE"

    # Multiple contenders: best < 2× second, multiple collections overlap
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
    uncovered_count = len(uncovered)

    # Semantic overlap: best match's rule_tags ∩ discovery candidate_tags
    semantic_overlap = False
    if best:
        rule_raw = cursor.execute(
            "SELECT rule_json FROM collections WHERE id=?", (best["id"],)
        ).fetchone()
        if rule_raw and rule_raw[0]:
            try:
                rule = json.loads(rule_raw[0])
                rule_tags = set(rule.get("tags", []) + rule.get("tags_or", []))
                disc_tags = set(group["candidate_tags"])
                semantic_overlap = bool(rule_tags & disc_tags)
            except (json.JSONDecodeError, TypeError):
                pass

    action = classify_action(
        covered_total=len(all_covered),
        uncovered_total=len(uncovered),
        best_match_count=best["covered_count"] if best else 0,
        second_best_count=second["covered_count"] if second else 0,
        semantic_overlap=semantic_overlap,
    )

    # resource_samples: 前 20 条资源 (title + covered status + collection objects)
    samples = []
    res_list = sorted(resource_ids)[:20]
    if res_list:
        placeholders = ",".join("?" * len(res_list))
        title_rows = {r[0]: r[1] for r in cursor.execute(
            f"SELECT res_id, title FROM resources WHERE res_id IN ({placeholders})",
            res_list).fetchall()}
        for rid in res_list:
            in_colls = []
            for m in matches:
                if cursor.execute("SELECT 1 FROM resource_collections WHERE resource_id=? AND collection_id=?",
                                  (rid, m["id"])).fetchone():
                    in_colls.append({"id": m["id"], "title": m["title"]})
            samples.append({
                "id": rid,
                "title": title_rows.get(rid, ""),
                "covered": rid in all_covered,
                "collections": in_colls,
            })

    # Generate reason text
    if action == "KEEP":
        reason = "全部资源已被已有专题覆盖"
    elif action == "EXPAND_RULE":
        if best:
            best_pct = round(100 * best["covered_count"] / total)
            reason = f"{best['title']} 已覆盖 {best['covered_count']}/{total} ({best_pct}%)。{uncovered_count}条未覆盖资源可通过调整 rule_json 补全"
        else:
            reason = "存在匹配专题但覆盖率不足"
    elif action == "MERGE_REVIEW":
        names = ", ".join(m["title"] for m in matches[:3])
        reason = f"多个专题覆盖相近: {names}"
    else:
        reason = "无专题显著覆盖此标签组合，建议人工评估是否创建新专题"

    return {
        "group_id": group.get("group_id", "-".join(group["candidate_tags"]).lower()[:80]),
        "candidate_tags": group["candidate_tags"],
        "representative_tags": group.get("representative_tags", []),
        "title_keywords": group.get("title_keywords", []),
        "match_count": total,
        "covered_count": len(all_covered),
        "uncovered_count": uncovered_count,
        "coverage_pct": round(100 * len(all_covered) / total) if total > 0 else 0,
        "uncovered_ids": sorted(uncovered)[:20],
        "best_match": best,
        "top_matches": matches[:5],
        "action": action,
        "action_icon": {
            "KEEP": "circle-check",
            "EXPAND_RULE": "wrench",
            "MERGE_REVIEW": "git-merge",
            "NEW_COLLECTION": "sparkles",
        }.get(action, "circle"),
        "action_label": {
            "KEEP": "已全覆盖",
            "EXPAND_RULE": "建议完善规则",
            "MERGE_REVIEW": "专题重叠",
            "NEW_COLLECTION": "新专题候选",
        }.get(action, action),
        "reason": reason,
        "resource_samples": samples,
    }


# ============================================================
# Output
# ============================================================

def print_terminal(results):
    print()
    print(f"{'Tag组':35s} {'发现':>4s} {'覆盖':>4s} {'未覆盖':>4s} {'动作':12s} {'最佳匹配'}")
    print("─" * 90)
    for r in results:
        tags_str = " ".join(r["candidate_tags"][:4])
        best_name = r["best_match"]["title"] if r["best_match"] else "—"
        print(f"{tags_str:35s} {r['match_count']:4d} {r['covered_count']:4d} {r['uncovered_count']:4d} {r['action_label']:12s} {best_name[:30]}")
        if r["action"] == "MERGE_REVIEW" and len(r["top_matches"]) >= 2:
            for m in r["top_matches"]:
                print(f"  {'':35s} └─ {m['title']:30s} 覆盖 {m['covered_count']}")
    print()

    # Summary
    counts = defaultdict(int)
    for r in results:
        counts[r["action"]] += 1
    print(f"总计: {len(results)} 个发现组")
    for action, label in [("KEEP","已全覆盖 (circle-check)"),("EXPAND_RULE","建议完善规则 (wrench)"),("MERGE_REVIEW","专题重叠 (git-merge)"),("NEW_COLLECTION","新专题候选 (sparkles)")]:
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

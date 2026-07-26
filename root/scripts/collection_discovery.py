#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BigPRC Collection Discovery — Tag 共现模式发现器 (Phase 5.3B)

职责: 扫描资源库，发现反复出现的 Tag 组合模式。
边界: 只读分析。不命名专题、不评分、不推荐、不推导 Rule、不写数据库。

算法:
  1. 筛选候选 Tags (频率 ≥5 + 非 Stop Tags)
  2. 对每条资源取候选 Tags, 生成 K-combinations (默认 K=3)
  3. GROUP BY tag 组合, COUNT(DISTINCT resource_id)
  4. 过滤 HAVING ≥ min-co (默认 5)

用法:
  python3 collection_discovery.py --scan                 # 默认扫描
  python3 collection_discovery.py --scan --min-tags 2    # 2-tag 组合
  python3 collection_discovery.py --scan --min-co 10     # 至少 10 条
  python3 collection_discovery.py --scan --json          # JSON 输出
  python3 collection_discovery.py --scan --no-stop-tags  # 不过滤 Stop Tags
  python3 collection_discovery.py --scan --json -o res.json

Config: 读取 /root/scripts/.env (DB_FILE)
"""

import os
import sys
import json
import sqlite3
import itertools
from collections import defaultdict
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
DB_FILE = os.getenv("DB_FILE")

if not DB_FILE:
    print("❌ DB_FILE not set")
    sys.exit(1)

# ============================================================
# Stop Tags (可配置)
# ============================================================

DEFAULT_STOP_TAGS = {
    "纪录片", "电子书", "课程", "软件", "游戏", "电影", "动画", "剧集", "PDF", "APK",
    "BBC", "Discovery", "IMAX", "国家地理", "History", "PBS", "CCTV",
    "工具", "资源", "其他", "视频", "音频", "合集", "书", "资料",
}

# ============================================================
# Core Algorithm
# ============================================================

def get_candidate_tags(cursor, stop_tags, min_freq=5):
    """Step 1: 筛选频率 ≥ min_freq 且非 Stop Tags 的候选标签."""
    stop_placeholders = ",".join("?" * len(stop_tags))
    rows = cursor.execute(f"""
        SELECT t.name, COUNT(DISTINCT rt.resource_id) as n
        FROM tags t
        JOIN resource_tags rt ON t.id = rt.tag_id
        WHERE t.name NOT IN ({stop_placeholders})
        GROUP BY t.name
        HAVING n >= ?
        ORDER BY n DESC
    """, list(stop_tags) + [min_freq]).fetchall()
    return {r[0] for r in rows}


def build_resource_tag_map(cursor, candidate_tags):
    """Step 2: 每条资源 → 候选 Tag 列表 (只保留候选集中的)."""
    rmap = defaultdict(list)
    # 批量查询: 所有 resource_tags JOIN tags, 筛选 candidate tags
    placeholders = ",".join("?" * len(candidate_tags))
    if not candidate_tags:
        return rmap
    rows = cursor.execute(f"""
        SELECT rt.resource_id, t.name
        FROM resource_tags rt JOIN tags t ON rt.tag_id = t.id
        WHERE t.name IN ({placeholders})
    """, list(candidate_tags)).fetchall()
    for res_id, tag_name in rows:
        rmap[res_id].append(tag_name)
    return rmap


def discover_groups(rmap, min_tags=3, min_co=5):
    """Step 3-4: 生成 K-combinations, GROUP BY, 过滤."""
    groups = defaultdict(set)
    for res_id, tags in rmap.items():
        # 按字母序排序确保组合可聚合
        tags_sorted = sorted(set(tags))
        for combo in itertools.combinations(tags_sorted, min_tags):
            groups[combo].add(res_id)

    # 过滤: ≥ min_co
    return {k: v for k, v in groups.items() if len(v) >= min_co}


def enrich_groups(cursor, groups):
    """Step 5: 补充 metadata — category 分布、示例资源."""
    result = []
    for tag_tuple, res_ids in groups.items():
        res_list = sorted(res_ids)
        count = len(res_list)

        # primary_categories
        cat_dist = defaultdict(int)
        for r in cursor.execute(
            "SELECT COALESCE(category,'?') FROM resources WHERE res_id IN ({})".format(
                ",".join("?" * len(res_list))),
            res_list
        ).fetchall():
            cat_dist[r[0]] += 1
        primary_cats = dict(sorted(cat_dist.items(), key=lambda x: -x[1])[:5])

        # samples
        samples = [r[0] for r in cursor.execute(
            "SELECT title FROM resources WHERE res_id IN ({}) LIMIT 3".format(
                ",".join("?" * min(5, len(res_list)))),
            res_list[:5]
        ).fetchall()]

        # coverage
        total = cursor.execute("SELECT COUNT(*) FROM resources").fetchone()[0]

        result.append({
            "candidate_tags": sorted(tag_tuple),
            "match_count": count,
            "coverage_pct": round(100 * count / total, 2),
            "primary_categories": primary_cats,
            "samples": samples,
            "resource_ids": res_list,
        })

    return sorted(result, key=lambda x: -x["match_count"])


# ============================================================
# Output
# ============================================================

def print_terminal(groups, params):
    print()
    print("=" * 65)
    print(f"  Collection Discovery — Tag 共现扫描")
    print("=" * 65)
    print(f"  全部资源: {params['total']}")
    print(f"  Stop Tags: {', '.join(sorted(params['stop_tags']))}")
    print(f"  参数: min-tags={params['min_tags']}  min-co={params['min_co']}")
    print(f"  发现: {len(groups)} 个 Tag 共现组")
    print()

    prev_cat = None
    for g in groups:
        top_cat = list(g["primary_categories"].keys())[0] if g["primary_categories"] else "?"
        if top_cat != prev_cat:
            print(f"── {top_cat} ──")
            prev_cat = top_cat

        tags_str = "  ".join(g["candidate_tags"])
        samples_str = " | ".join(s[:50] for s in g["samples"])
        print(f"  {g['match_count']:4d}条  {tags_str}")
        print(f"        {samples_str}")
    print(f"\n── 总计: {len(groups)} 个 Tag 共现组 ──")
    print()


def print_json(groups, params):
    print(json.dumps({
        "scan_time": __import__("datetime").datetime.now().isoformat(),
        "params": params,
        "groups_found": len(groups),
        "groups": groups,
    }, ensure_ascii=False))


# ============================================================
# CLI
# ============================================================

def main():
    scan = "--scan" in sys.argv
    json_out = "--json" in sys.argv
    min_tags = 3
    min_co = 5
    no_stop = "--no-stop-tags" in sys.argv
    out_file = None

    for i, a in enumerate(sys.argv):
        if a == "--min-tags" and i+1 < len(sys.argv):
            min_tags = int(sys.argv[i+1])
        if a == "--min-co" and i+1 < len(sys.argv):
            min_co = int(sys.argv[i+1])
        if a == "--stop-tags" and i+1 < len(sys.argv):
            DEFAULT_STOP_TAGS.update(set(sys.argv[i+1].split(",")))
        if a == "-o" and i+1 < len(sys.argv):
            out_file = sys.argv[i+1]

    if not scan:
        print("Usage: python3 collection_discovery.py --scan [options]")
        print("  --scan              Scan for tag co-occurrence groups")
        print("  --min-tags N        Min tags per group (default 3)")
        print("  --min-co N          Min resources sharing a group (default 5)")
        print("  --json              Output as JSON")
        print("  --no-stop-tags      Disable Stop Tags filter")
        print("  --stop-tags 'a,b'   Add custom Stop Tags (comma-separated)")
        print("  -o <file>           Write JSON to file")
        return

    stop_tags = set() if no_stop else DEFAULT_STOP_TAGS

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    total = cursor.execute("SELECT COUNT(*) FROM resources").fetchone()[0]

    # Step 1: 候选 Tags
    cand_tags = get_candidate_tags(cursor, stop_tags, min_freq=min_co)

    # Step 2: 资源 → 候选 Tag 列表
    rmap = build_resource_tag_map(cursor, cand_tags)

    # Step 3-4: 组合 → 分组 → 过滤
    groups = discover_groups(rmap, min_tags=min_tags, min_co=min_co)

    # Step 5: 补充 metadata
    results = enrich_groups(cursor, groups)

    conn.close()

    params = {
        "total": total, "min_tags": min_tags, "min_co": min_co,
        "stop_tags": sorted(stop_tags), "candidate_tags_count": len(cand_tags),
    }

    if json_out:
        output = json.dumps({
            "scan_time": __import__("datetime").datetime.now().isoformat(),
            "params": params,
            "groups_found": len(results),
            "groups": results,
        }, ensure_ascii=False)
        if out_file:
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"✅ Written to {out_file}")
        else:
            print(output)
    else:
        print_terminal(results, params)


if __name__ == "__main__":
    main()

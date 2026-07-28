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
    print("❌ DB_FILE not set in .env")
    print("   Add: DB_FILE=/root/scripts/database.db")
    sys.exit(1)

# Tag normalize constants (inlined from tag_normalize to avoid import-side-effect)
BRAND_NORMALIZE = {
    "安卓": "Android", "安卓应用": "Android", "安卓软件": "Android",
    "安卓工具": "Android", "android": "Android",
    "windows": "Windows", "Windows7": "Windows", "Windows10": "Windows",
    "Windows11": "Windows", "windows软件": "Windows", "windows工具": "Windows",
    "macos": "Mac", "mac": "Mac", "apple": "Apple",
    "nationalgeographic": "国家地理", "natgeo": "国家地理", "nat geo": "国家地理",
    "imax": "IMAX", "bbc": "BBC", "discovery": "Discovery",
    "historychannel": "History", "pbs": "PBS", "cctv": "CCTV",
}
SPELLING_FIX = {
    "视频编辑": "视频剪辑", "视频制作": "视频剪辑", "影像编辑": "视频剪辑",
    "影片剪辑": "视频剪辑", "剪辑视频": "视频剪辑", "剪映": "视频剪辑",
    "capcut": "视频剪辑", "直播电商": "直播带货", "电商直播": "直播带货",
    "自媒体运营": "自媒体", "新媒体运营": "自媒体", "短视频运营": "自媒体",
}
TYPE_TAGS = {"纪录片", "电影", "动画", "剧集", "电子书", "课程", "软件",
             "PDF", "APK", "游戏", "模组", "模板", "素材"}
BRAND_TAGS = {"BBC", "Discovery", "IMAX", "国家地理", "History", "PBS",
              "CCTV", "Apple", "Google", "Microsoft", "Adobe", "OpenAI",
              "Android", "Windows", "Mac", "Linux", "iOS"}

# ============================================================
# Stop Tags (可配置)
# ============================================================

DEFAULT_STOP_TAGS = {
    "纪录片", "电子书", "课程", "软件", "游戏", "电影", "动画", "剧集", "PDF", "APK",
    "BBC", "Discovery", "IMAX", "国家地理", "History", "PBS", "CCTV",
    "工具", "资源", "其他", "视频", "音频", "合集", "书", "资料",
}


# ============================================================
# Tag Normalize (内存, 不写库)
# ============================================================

def normalize_tag(name):
    """应用 tag_normalize 规则, 返回 canonical 名称."""
    # ① Brand normalize
    if name.lower() in BRAND_NORMALIZE:
        return BRAND_NORMALIZE[name.lower()]
    if name in BRAND_NORMALIZE:
        return BRAND_NORMALIZE[name]
    # ② Spelling fix
    if name in SPELLING_FIX:
        return SPELLING_FIX[name]
    # ③ Compound split: "BBC纪录片" -> None (discard, keeps brand + type separate)
    for brand in BRAND_TAGS:
        for ttype in TYPE_TAGS:
            if name == brand + ttype:
                return None
    return name


def get_normalized_tags(cursor):
    """返回 {tag_id: canonical_name} 映射 (内存, 不写库)."""
    mapping = {}
    for row in cursor.execute("SELECT id, name FROM tags").fetchall():
        n = normalize_tag(row[1])
        if n:
            mapping[row[0]] = n
    return mapping


def apply_normalize_to_rmap(rmap, tag_id_to_name):
    """将 rmap 中的 tag_id 替换为 normalized name, 去重."""
    normalized = defaultdict(set)
    for res_id, tag_ids in rmap.items():
        for tid in tag_ids:
            name = tag_id_to_name.get(tid)
            if name:
                normalized[res_id].add(name)
    return normalized


# ============================================================
# Title Stop Words (关键词提取用)
# ============================================================

TITLE_STOP_WORDS = {
    "的", "和", "与", "及", "或", "是", "了", "在", "为", "等",
    "全", "新", "版", "本", "大", "中", "小", "上", "下", "之",
    "第", "一", "个", "部", "套", "册", "卷", "篇", "集", "期",
    "年", "月", "日", "1", "2", "3", "4", "5",
    "720P", "1080P", "1080p", "720p", "4K", "高清", "超清", "蓝光",
    "BBC", "Discovery", "IMAX", "国家地理", "CCTV",
}

# ============================================================
# Core Algorithm
# ============================================================

def get_candidate_tags(cursor, stop_tags, tag_norm, min_freq=5):
    """Step 1: 筛选频率 ≥ min_freq 且非 Stop Tags 的候选标签 (使用 normalized names)."""
    # 统计 normalized tag 频率
    norm_counts = defaultdict(int)
    for row in cursor.execute("""
        SELECT rt.resource_id, rt.tag_id
        FROM resource_tags rt
    """).fetchall():
        name = tag_norm.get(row[1])
        if name and name not in stop_tags:
            norm_counts[name] += 1

    # 去重 per resource (同一 normalized tag 在同一资源只算一次)
    unique_counts = defaultdict(int)
    for row in cursor.execute("""
        SELECT DISTINCT rt.resource_id, rt.tag_id
        FROM resource_tags rt
    """).fetchall():
        name = tag_norm.get(row[1])
        if name and name not in stop_tags:
            unique_counts[name] += 1

    return {name for name, cnt in unique_counts.items() if cnt >= min_freq}


def build_resource_tag_map(cursor, candidate_tags, tag_norm):
    """Step 2: 每条资源 → 候选 Normalized Tag 列表 (去重)."""
    rmap = defaultdict(set)
    for row in cursor.execute("SELECT rt.resource_id, rt.tag_id FROM resource_tags rt").fetchall():
        name = tag_norm.get(row[1])
        if name and name in candidate_tags:
            rmap[row[0]].add(name)
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



# ============================================================
# Maximal Itemset Dedup
# ============================================================

def maximal_itemsets(groups):
    """去重：如果 A 的 tags 是 B 的 strict subset,
       且 A 的 resource_ids 是 B 的 subset (>80% 重叠),
       则删除 A (保留 maximal B).

    groups: {tag_tuple: set(resource_ids)}
    Returns: filtered dict
    """
    items = list(groups.items())  # [(tags, ids), ...]
    items.sort(key=lambda x: -len(x[1]))  # sort by resource count desc

    keep = {}
    for tags_a, ids_a in items:
        is_subsumed = False
        for tags_b, ids_b in items:
            if tags_a == tags_b:
                continue
            if set(tags_a) < set(tags_b):  # strict subset
                overlap = len(ids_a & ids_b)
                if overlap / max(len(ids_a), 1) > 0.8:
                    is_subsumed = True
                    break
        if not is_subsumed:
            keep[tags_a] = ids_a
    return keep


def extract_representative_tags(cursor, res_ids, group_tags, top_n=8):
    """统计匹配资源中除 group_tags 外的其他高频 Tag."""
    counts = defaultdict(int)
    for row in cursor.execute("""
        SELECT t.name FROM resource_tags rt
        JOIN tags t ON rt.tag_id = t.id
        WHERE rt.resource_id IN ({})
    """.format(",".join("?" * len(res_ids))), res_ids).fetchall():
        if row[0] not in group_tags and row[0] not in DEFAULT_STOP_TAGS:
            counts[row[0]] += 1
    return [t for t, _ in sorted(counts.items(), key=lambda x: -x[1])[:top_n]]


def extract_title_keywords(cursor, res_ids, top_n=10):
    """从匹配资源标题中提取高频词 (去停用词)."""
    word_freq = defaultdict(int)
    for row in cursor.execute("""
        SELECT title FROM resources WHERE res_id IN ({})
    """.format(",".join("?" * len(res_ids))), res_ids).fetchall():
        title = row[0] or ""
        # 简单分词: 按常见分隔符切分
        import re
        tokens = re.split(r'[\s·\-—、《》（）()\[\]【】,，。.：:！!？?~|/]+', title)
        for token in tokens:
            token = token.strip()
            if len(token) >= 2 and token not in TITLE_STOP_WORDS and not token.isdigit():
                word_freq[token] += 1
    # 去低频 (只在 ≤2 条资源中出现)
    return [w for w, _ in sorted(word_freq.items(), key=lambda x: -x[1])[:top_n] if word_freq[w] >= 3]


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
            "group_id": "-".join(sorted(tag_tuple)).lower()[:80],
            "candidate_tags": sorted(tag_tuple),
            "match_count": count,
            "coverage_pct": round(100 * count / total, 2),
            "primary_categories": primary_cats,
            "samples": samples,
            "resource_ids": res_list,
        })

        result[-1]["representative_tags"] = extract_representative_tags(
            cursor, res_list, set(tag_tuple))
        result[-1]["title_keywords"] = extract_title_keywords(cursor, res_list)

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

    # Build normalized tag mapping (memory only)
    tag_norm = get_normalized_tags(cursor)

    # Step 1: 候选 Tags
    cand_tags = get_candidate_tags(cursor, stop_tags, tag_norm, min_freq=min_co)

    # Step 2: 资源 → 候选 Normalized Tag 列表
    rmap = build_resource_tag_map(cursor, cand_tags, tag_norm)

    # Step 3-4: 组合 → 分组 → 过滤
    raw_groups = discover_groups(rmap, min_tags=min_tags, min_co=min_co)

    # Step 4.5: Maximal Itemset 去重
    groups = maximal_itemsets(raw_groups)

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

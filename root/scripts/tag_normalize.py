#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BigPRC tag_normalize.py — Tag 治理：碎片标签归一化为标准标签 (P1-2.5)

自动识别并合并碎片标签:
  "BBC纪录片" → "BBC" (content → brand)
  "野生动物" → "动物" (specific → general, via alias)
  "道家"     → "道教"
  "符咒/符箓"  → "道教"

策略:
  1. 品牌+类型合并: "BBC纪录片" → 只保留 "BBC" (类型标签"纪录片"独立存在)
  2. 近义词合并:    "道家" → "道教", "符咒" → "道教"
  3. 低频标签 (count=1): 如果包含某个高频词的子串, 合并

用法:
  python3 tag_normalize.py --plan       # 预览合并计划
  python3 tag_normalize.py --dry-run    # 模拟执行, 不写库
  python3 tag_normalize.py              # 执行归一化
"""

import os
import sys
import sqlite3
import re
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
DB_FILE = os.getenv("DB_FILE")

if not DB_FILE:
    print("❌ DB_FILE not set")
    sys.exit(1)

# ============================================================
# 1. 合并规则
# ============================================================

# 高频 Type 标签 (品牌/类型应该独立存在)
TYPE_TAGS = {"纪录片", "电影", "动画", "剧集", "电子书", "课程", "软件", "游戏", "模组", "PDF"}

# 品牌标签
BRAND_TAGS = {"BBC", "Discovery", "IMAX", "NationalGeographic", "国家地理", "History",
              "PBS", "CCTV", "Apple", "Google", "Microsoft", "Adobe", "OpenAI"}

# 近义词映射 (fragment → canonical)
SYNONYM_MAP = {
    "道家": "道教",
    "符咒": "道教",
    "符箓": "道教",
    "符录": "道教",
    "咒语": "道教",
    "科仪": "道教",
    "经文": "道教",
    "手抄本": "古籍",
    "古籍经典": "古籍",
    "野生动物": "动物",
    "自然生态": "自然",
    "海洋生物": "海洋",
    "宇宙探索": "宇宙",
    "太空探索": "宇宙",
    "历史纪录": "历史",
    "编程开发": "编程",
    "软件开发": "编程",
    "视频剪辑": "剪辑",
    "视频编辑": "剪辑",
    "短视频": "剪辑",
    "直播带货": "运营",
    "电商": "运营",
    "安卓": "Android",
    "安卓软件": "Android",
    "安卓应用": "Android",
    "Windows软件": "Windows",
    "Windows工具": "Windows",
}

# 品牌+类型 合并规则: "BBC纪录片" → only "BBC" (不重复加"纪录片")
def split_brand_type(name):
    """如果标签是 "品牌+类型" 的复合形式, 返回 (brand, type) 对, 否则 None."""
    for brand in BRAND_TAGS:
        for ttype in TYPE_TAGS:
            if name == brand + ttype:
                return brand
    return None


def find_synonym(name):
    """检查是否是已知近义词, 返回 canonical 名称."""
    return SYNONYM_MAP.get(name)


def normalize_one(name, high_freq_tags):
    """对单个标签名做归一化, 返回 canonical 名称列表 (通常 1 个)."""
    # 1. 品牌+类型: "BBC纪录片" → "BBC"
    brand = split_brand_type(name)
    if brand:
        return [brand]

    # 2. 近义词: "道家" → "道教"
    syn = find_synonym(name)
    if syn:
        return [syn]

    # 3. 低频标签包含高频词: "BBC自然纪录片" → 如果"BBC"和"自然"都是高频, 保留标签本身(已原子化)
    # 检查是否可以用高频词拆分
    parts = []
    remaining = name
    for hf in sorted(high_freq_tags, key=lambda x: -len(x)):
        if hf != name and hf in remaining:
            parts.append(hf)
            remaining = remaining.replace(hf, "")
    if parts and not remaining.strip():
        return parts  # 拆分成功

    return None  # 无法归一化, 保留原标签


# ============================================================
# 2. 主流程
# ============================================================

def main():
    dry_run = "--dry-run" in sys.argv
    plan_only = "--plan" in sys.argv

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 确保 tag_aliases 表存在
    cursor.execute("CREATE TABLE IF NOT EXISTS tag_aliases (alias TEXT PRIMARY KEY, target TEXT NOT NULL, reason TEXT DEFAULT 'auto')")

    # 获取高频标签 (count >= 5)
    high_freq = set(r[0] for r in cursor.execute(
        "SELECT name FROM tags WHERE count >= 5"
    ).fetchall())

    # 扫描所有标签
    all_tags = cursor.execute("SELECT id, name, count FROM tags ORDER BY count DESC").fetchall()
    print(f"📊 Total unique tags: {len(all_tags)}")
    print()

    merges = []  # (alias_name, target_name, reason)

    for tag_id, name, count in all_tags:
        result = normalize_one(name, high_freq)
        if result:
            for target in result:
                if target != name:
                    merges.append((name, target, f"auto: compound→{target}"))

    print(f"🔀 Merge candidates: {len(merges)}")
    if merges:
        print()
        for alias, target, reason in merges:
            print(f"  {alias:30s} → {target}  ({reason})")
    print()

    if plan_only:
        conn.close()
        return

    if dry_run:
        print("🧪 DRY-RUN — no changes made.")
        conn.close()
        return

    if not merges:
        print("✅ No merges needed.")
        conn.close()
        return

    # 执行合并
    for alias, target, reason in merges:
        # 1. 写入 alias 映射
        cursor.execute("INSERT OR IGNORE INTO tag_aliases (alias, target, reason) VALUES (?,?,?)",
                       (alias, target, reason))

        # 2. 找到 target tag id
        target_row = cursor.execute("SELECT id FROM tags WHERE name=?", (target,)).fetchone()
        if not target_row:
            continue
        target_id = target_row[0]

        # 3. 迁移 resource_tags
        alias_row = cursor.execute("SELECT id FROM tags WHERE name=?", (alias,)).fetchone()
        if not alias_row:
            continue
        alias_id = alias_row[0]

        # 把指向 alias 的 resource_tags 指向 target
        cursor.execute("""
            UPDATE resource_tags SET tag_id=?, score=MAX(score, 0.7)
            WHERE tag_id=?
        """, (target_id, alias_id))

        # 更新 target count
        cursor.execute("""
            UPDATE tags SET count = (SELECT COUNT(*) FROM resource_tags WHERE tag_id=?)
            WHERE id=?
        """, (target_id, target_id))

        # 4. 删除孤儿 fragment tag
        cursor.execute("DELETE FROM resource_tags WHERE tag_id=?", (alias_id,))
        cursor.execute("DELETE FROM tags WHERE id=?", (alias_id,))

    conn.commit()

    # 最终统计
    final_unique = cursor.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    removed = len(all_tags) - final_unique
    print(f"✅ Normalized: {len(merges)} merges, removed {removed} fragment tags")
    print(f"   Before: {len(all_tags)} unique tags")
    print(f"   After:  {final_unique} unique tags")
    print()
    print("   Run 'python3 tag_normalize.py' again to check for more merges.")

    conn.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BigPRC tag_normalize.py — Tag 治理 (Phase 1: 品牌统一 + 拼写修复) (P1-2.5)

Phase 1 策略 (保守, 不破坏专题粒度):
  ① 品牌统一:  安卓/安卓应用 → Android, NationalGeographic → 国家地理
  ② 复合拆分:  "BBC纪录片" → "BBC" (类型标签"纪录片"独立保留)
  ③ 拼写统一:  视频编辑 → 视频剪辑, Windows7 → Windows
  ④ 大小写:    bbc → BBC, android → Android, imax → IMAX

不合并的内容:
  - 近义词: 道家≠道教, 野生动物≠动物, 自然≠动物
  - 层级:   符箓/符咒/科仪 各自独立 (未来专题子类)
  - 品牌:   BBC/Discovery/IMAX 各自独立

用法:
  python3 tag_normalize.py --plan       # 预览合并计划
  python3 tag_normalize.py --dry-run    # 模拟执行
  python3 tag_normalize.py              # 执行归一化
"""

import os
import sys
import sqlite3
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
DB_FILE = os.getenv("DB_FILE")

if not DB_FILE:
    print("❌ DB_FILE not set")
    sys.exit(1)

# ============================================================
# Phase 1 规则: 仅做品牌统一 + 拼写修复
# ============================================================

# ① 品牌拼写统一 (variants → canonical)
BRAND_NORMALIZE = {
    # Android 分裂
    "安卓":        "Android",
    "安卓应用":     "Android",
    "安卓软件":     "Android",
    "安卓工具":     "Android",
    "android":     "Android",
    # Windows 分裂
    "windows":     "Windows",
    "Windows7":    "Windows",
    "Windows10":   "Windows",
    "Windows11":   "Windows",
    "windows软件":  "Windows",
    "windows工具":  "Windows",
    # Mac
    "macos":       "Mac",
    "mac":         "Mac",
    "apple":       "Apple",
    # 品牌
    "nationalgeographic": "国家地理",
    "natgeo":             "国家地理",
    "nat geo":            "国家地理",
    # IMAX
    "imax":        "IMAX",
    # BBC
    "bbc":         "BBC",
    # Discovery
    "discovery":   "Discovery",
    # History Channel
    "historychannel": "History",
    # PBS
    "pbs":         "PBS",
    # CCTV
    "cctv":        "CCTV",
}

# ② 拼写/格式修复
SPELLING_FIX = {
    "视频编辑": "视频剪辑",
    "视频制作": "视频剪辑",
    "影像编辑": "视频剪辑",
    "影片剪辑": "视频剪辑",
    "剪辑视频": "视频剪辑",
    "剪映":     "视频剪辑",
    "capcut":   "视频剪辑",
    # 直播
    "直播电商": "直播带货",
    "电商直播": "直播带货",
    # 运营
    "自媒体运营": "自媒体",
    "新媒体运营": "自媒体",
    "短视频运营": "自媒体",
}

# ③ 类型标签 (复合拆分时使用)
TYPE_TAGS = {"纪录片", "电影", "动画", "剧集", "电子书", "课程", "软件",
             "PDF", "APK", "游戏", "模组", "模板", "素材"}

# ④ 品牌标签 (复合拆分时保留品牌)
BRAND_TAGS = {"BBC", "Discovery", "IMAX", "国家地理", "History", "PBS",
              "CCTV", "Apple", "Google", "Microsoft", "Adobe", "OpenAI",
              "Android", "Windows", "Mac", "Linux", "iOS"}


def normalize_all_tags(cursor):
    """扫描所有标签, 生成 (alias → target) 合并列表."""
    all_tags = cursor.execute(
        "SELECT id, name, count FROM tags ORDER BY count DESC"
    ).fetchall()

    merges = []  # (tag_id, alias_name, target_name, reason)

    for tag_id, name, count in all_tags:
        name_lower = name.lower().strip()

        # ① 品牌拼写统一
        if name_lower in BRAND_NORMALIZE:
            target = BRAND_NORMALIZE[name_lower]
            if target != name:
                merges.append((tag_id, name, target, "brand_normalize"))

        # ② 拼写修复
        if name in SPELLING_FIX:
            target = SPELLING_FIX[name]
            merges.append((tag_id, name, target, "spelling_fix"))

        # ③ 复合拆分: "BBC纪录片" → "BBC" (保留品牌, 类型独立)
        for brand in BRAND_TAGS:
            for ttype in TYPE_TAGS:
                if name == brand + ttype:
                    merges.append((tag_id, name, brand, "compound: " + name + " → " + brand))
                    break

    return merges


def execute_merges(cursor, merges):
    """执行合并: 迁移 resource_tags → 删除 fragment tag."""
    aliases_added = 0
    tags_removed = 0

    for tag_id, alias, target, reason in merges:
        # 1. 记录 alias 映射
        cursor.execute(
            "INSERT OR IGNORE INTO tag_aliases (alias, target, reason) VALUES (?,?,?)",
            (alias, target, reason))

        # 2. 找到 target tag
        target_row = cursor.execute("SELECT id FROM tags WHERE name=?", (target,)).fetchone()
        if not target_row:
            # target 不存在, 重命名当前 tag
            cursor.execute("UPDATE tags SET name=? WHERE id=?", (target, tag_id))
            aliases_added += 1
            continue
        target_id = target_row[0]

        # 3. 迁移 resource_tags 指向
        cursor.execute(
            "UPDATE resource_tags SET tag_id=?, score=MAX(score, 0.7) WHERE tag_id=?",
            (target_id, tag_id))

        # 4. 重算 target count
        cursor.execute(
            "UPDATE tags SET count=(SELECT COUNT(*) FROM resource_tags WHERE tag_id=?) WHERE id=?",
            (target_id, target_id))

        # 5. 删除 fragment tag
        cursor.execute("DELETE FROM resource_tags WHERE tag_id=?", (tag_id,))
        cursor.execute("DELETE FROM tags WHERE id=?", (tag_id,))
        tags_removed += 1

    return aliases_added, tags_removed


def main():
    dry_run = "--dry-run" in sys.argv
    plan_only = "--plan" in sys.argv

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 确保表结构
    cursor.execute("CREATE TABLE IF NOT EXISTS tag_aliases (alias TEXT PRIMARY KEY, target TEXT NOT NULL, reason TEXT DEFAULT 'auto')")

    merges = normalize_all_tags(cursor)

    print(f"📊 Total unique tags: {cursor.execute('SELECT COUNT(*) FROM tags').fetchone()[0]}")
    print(f"🔀 Merge candidates: {len(merges)}")
    print()

    if merges:
        for tag_id, alias, target, reason in merges:
            print(f"  {alias:30s} → {target:20s}  ({reason})")
    print()

    if plan_only:
        conn.close()
        return

    if dry_run:
        print("🧪 DRY-RUN — no changes made.")
        conn.close()
        return

    if not merges:
        print("✅ Already clean.")
        conn.close()
        return

    added, removed = execute_merges(cursor, merges)
    conn.commit()

    final = cursor.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    print(f"✅ Phase 1 done: {added} renamed, {removed} removed fragments")
    print(f"   Before: {cursor.execute('SELECT COUNT(*) FROM tags').fetchone()[0] + removed} unique tags")
    print(f"   After:  {final} unique tags")
    print()

    # Set tag_type for known brands
    for brand in BRAND_TAGS:
        cursor.execute("UPDATE tags SET tag_type='brand' WHERE name=?", (brand,))
    for ttype in TYPE_TAGS:
        cursor.execute("UPDATE tags SET tag_type='category' WHERE name=?", (ttype,))
    cursor.execute("UPDATE tags SET tag_type='platform' WHERE name IN ('Android','Windows','Mac','Linux','iOS','Web')")
    conn.commit()

    conn.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BigPRC SEO Content Cleanup — 针对性修复残留营销词/通用词 (不调用 AI)

修复内容:
  1. tagline 中的 "必备""首选""神器" → 删除该词 (保留其余文字)
  2. ai_keywords 中的 "免费" → 从 JSON 数组中移除

用法:
  python3 seo_content_cleanup.py --plan    # 预览受影响行
  python3 seo_content_cleanup.py           # 执行修复

Config: 读取 /root/scripts/.env (DB_FILE)
"""

import os
import sys
import json
import sqlite3
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
DB_FILE = os.getenv("DB_FILE")

if not DB_FILE:
    print("❌ DB_FILE not set")
    sys.exit(1)

# ============================================================
# 修复规则
# ============================================================

TAGLINE_BAD_WORDS = ["必备", "首选", "神器"]
KEYWORD_BAD_WORDS = ["免费"]


def cleanup_tagline(cursor, plan_only=False):
    """修复 tagline 中的营销词."""
    fixed = 0
    for word in TAGLINE_BAD_WORDS:
        rows = cursor.execute(
            "SELECT resource_id, tagline FROM resource_content WHERE tagline LIKE ?",
            (f"%{word}%",)
        ).fetchall()

        for res_id, tagline in rows:
            new_tagline = tagline.replace(word, "").strip().rstrip("，,。.")
            if new_tagline != tagline:
                if plan_only:
                    print(f"  tagline: {res_id}  \"{word}\" → \"{new_tagline[:40]}\"")
                else:
                    cursor.execute(
                        "UPDATE resource_content SET tagline=? WHERE resource_id=?",
                        (new_tagline, res_id))
                    fixed += 1
    return fixed


def cleanup_keywords(cursor, plan_only=False):
    """从 ai_keywords JSON 数组中移除通用词."""
    fixed = 0
    for word in KEYWORD_BAD_WORDS:
        rows = cursor.execute(
            "SELECT resource_id, ai_keywords FROM resource_content WHERE ai_keywords LIKE ?",
            (f"%\"{word}\"%",)
        ).fetchall()

        for res_id, kws_json in rows:
            try:
                kws = json.loads(kws_json)
            except (json.JSONDecodeError, TypeError):
                continue

            if word in kws:
                new_kws = [kw for kw in kws if kw != word]
                new_json = json.dumps(new_kws, ensure_ascii=False)
                if plan_only:
                    print(f"  keywords: {res_id}  removed \"{word}\" → {new_kws}")
                else:
                    cursor.execute(
                        "UPDATE resource_content SET ai_keywords=? WHERE resource_id=?",
                        (new_json, res_id))
                    fixed += 1
    return fixed


def main():
    plan_only = "--plan" in sys.argv

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if plan_only:
        print("🔍 Preview — no changes will be made.\n")

    tf = cleanup_tagline(cursor, plan_only)
    kf = cleanup_keywords(cursor, plan_only)

    if not plan_only:
        conn.commit()
        print(f"✅ Fixed: {tf} taglines + {kf} keywords")
    else:
        print(f"\n📋 Will fix: {tf} taglines + {kf} keywords")
        print("   Run without --plan to apply.")

    conn.close()


if __name__ == "__main__":
    main()

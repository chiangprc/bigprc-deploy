#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BigPRC ai_tag_generator.py — AI 标签提取器 (P1-2)

输入: resources (title + ai_keywords + ai_summary + category + seo_desc)
输出: tags 表 + resource_tags 表

每一条资源调用一次 AI，输出 5-10 个标准化标签，自动合并去重、计算热度。

用法:
  python3 ai_tag_generator.py --plan          # 统计待标记数量
  python3 ai_tag_generator.py --limit 10      # 灰度测试
  python3 ai_tag_generator.py                 # 全量提取
  python3 ai_tag_generator.py --force         # 覆盖已有标签

Config: 读取 /root/scripts/.env (DB_FILE, API_BASE_URL, API_KEY)
"""

import os
import sys
import json
import re
import time
import sqlite3
import argparse
from dotenv import load_dotenv
from openai import OpenAI

# ============================================================
# 1. 配置
# ============================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))

API_BASE_URL = os.getenv("API_BASE_URL")
API_KEY      = os.getenv("API_KEY")
DB_FILE      = os.getenv("DB_FILE")

if not DB_FILE:
    print("❌ DB_FILE not set in .env")
    sys.exit(1)
if not API_KEY:
    print("❌ API_KEY not set in .env")
    sys.exit(1)

client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL, timeout=30.0)

MODEL = "deepseek-chat"

# ============================================================
# 2. 数据库
# ============================================================

def ensure_tables(cursor):
    """确保 tags / resource_tags 表存在."""
    existing = set(r[0] for r in cursor.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall())
    if "tags" not in existing or "resource_tags" not in existing:
        print("❌ tags / resource_tags 表不存在, 请先运行 migration 009.")
        print("   python3 migration.py up")
        sys.exit(1)


def get_untagged(cursor, force=False, limit=None):
    """查询待标记的资源 (resource_tags 为空, 或 --force)."""
    if force:
        where = "1=1"
    else:
        where = """r.res_id NOT IN (
            SELECT DISTINCT resource_id FROM resource_tags
        )"""

    query = f"""
        SELECT r.res_id, r.title, r.category,
               COALESCE(rc.ai_keywords, '') AS ai_keywords,
               COALESCE(rc.ai_summary, '')  AS ai_summary,
               COALESCE(r.seo_desc, '')     AS seo_desc
        FROM resources r
        LEFT JOIN resource_content rc ON r.res_id = rc.resource_id
        WHERE {where}
        ORDER BY r.res_id
    """
    if limit:
        query += f" LIMIT {int(limit)}"
    return cursor.execute(query).fetchall()


def save_tags(cursor, res_id, tags_with_score):
    """写入标签: 自动合并去重.

    tags_with_score: [{"name":"BBC","score":0.99}, ...]
    """
    for item in tags_with_score:
        name = item["name"].strip()
        score = item.get("score", 0.5)
        if not name or len(name) < 2:
            continue

        slug = _slugify(name)

        # upsert tag
        cursor.execute("""
            INSERT INTO tags (name, slug, type, count)
            VALUES (?, ?, 'topic', 1)
            ON CONFLICT(slug) DO UPDATE SET count = tags.count + 1
        """, (name, slug))
        tag_id = cursor.execute("SELECT id FROM tags WHERE slug=?", (slug,)).fetchone()[0]

        # link resource → tag
        cursor.execute("""
            INSERT OR REPLACE INTO resource_tags (resource_id, tag_id, score, source)
            VALUES (?, ?, ?, 'ai')
        """, (res_id, tag_id, score))


def _slugify(name):
    """中文/英文友好的 slug 生成."""
    s = name.strip().lower()
    s = re.sub(r'[^\w一-鿿-]', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')


# ============================================================
# 3. AI 标签提取
# ============================================================

def build_prompt(title, category, ai_keywords, ai_summary, seo_desc):
    """构造标签提取 prompt."""
    parts = [f"Title: {title}"]
    if category:      parts.append(f"Category: {category}")
    if ai_keywords:   parts.append(f"Existing keywords: {ai_keywords}")
    if ai_summary:    parts.append(f"Summary: {ai_summary[:100]}")
    if seo_desc:      parts.append(f"Description: {seo_desc[:200]}")
    context = "\n".join(parts)

    return f"""Extract 4-6 atomic tags for this resource. Tags form a discovery graph — users click one tag to find all related resources.

{context}

Output a JSON array: [{{"name":"BBC","score":0.99}}, {{"name":"海洋","score":0.90}}]

CRITICAL — Tag Atomicity Rules:
① ONE concept per tag. NEVER combine concepts into compound tags.
   WRONG: "BBC纪录片" "野生动物迁徙" "自然科普" "海洋纪录片" "AI编程工具"
   RIGHT: "BBC" + "纪录片" — decompose into independent atoms
   RIGHT: "野生动物" + "迁徙" — two separate concepts
   RIGHT: "自然" + "科普" — atomic, reusable

② Tag length: max 6 Chinese characters (person/organization names excepted).
   WRONG: "野生动物迁徙" (too long, compound)
   RIGHT: "野生动物" or "迁徙"

③ NEVER include resolution/quality metadata:
   WRONG: "4K" "1080P" "HDR" "蓝光" "超清" "高清版"
   These are display attributes, not discovery tags.

④ NEVER include version numbers, years, file extensions:
   WRONG: "v2.0" "2024" "PDF" "mp4" ".apk"

⑤ Brand/Source tags (atomic, original name):
   BBC / Discovery / IMAX / NationalGeographic / History / PBS / CCTV
   Apple / Google / Microsoft / Adobe / OpenAI

⑥ Type tags (pick 0-1):
   纪录片 / 电影 / 剧集 / 动画 / 软件 / 课程 / 电子书 / 游戏

⑦ Topic tags (pick 2-4 specific, reusable concepts):
   海洋 / 动物 / 宇宙 / 历史 / 战争 / 自然 / 科技 / AI /
   编程 / 设计 / 摄影 / 音乐 / 建筑 / 美食 / 旅行 /
   英语 / 数学 / 物理 / 心理学 / 经济学 / 哲学 /
   道教 / 佛教 / 中医 / 古籍 / 书法 / 绘画

⑧ Score: 0.9+ = explicit in title, 0.7-0.9 = from keywords/description, <0.7 = inferred.
   Use Chinese names for topics, original names for brands.

⑨ ONLY use tags from the lists above or very close variants. Do NOT invent new topic names.
   If a concept fits none, skip it rather than invent a one-off tag.

⑩ 4-6 tags total. More is NOT better — precision over quantity.

JSON only:
[{{"name":"BBC","score":0.99}},{{"name":"纪录片","score":0.97}},{{"name":"海洋","score":0.90}},{{"name":"动物","score":0.82}}]"""


def extract_tags(title, category="", ai_keywords="", ai_summary="", seo_desc=""):
    """调用 AI 提取标签, 返回 [{"name","score"}, ...] 或 None."""
    prompt = build_prompt(title, category, ai_keywords, ai_summary, seo_desc)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)

        # Handle both array and {"tags": [...]} formats
        if isinstance(data, dict):
            tags = data.get("tags", [])
        elif isinstance(data, list):
            tags = data
        else:
            return None

        if not tags or len(tags) < 2:
            return None

        # Validate & deduplicate
        seen = set()
        result = []
        for t in tags:
            if not isinstance(t, dict):
                continue
            name = str(t.get("name", "")).strip()
            score = float(t.get("score", 0.5))
            if name and name.lower() not in seen and score > 0.3:
                seen.add(name.lower())
                result.append({"name": name, "score": min(score, 1.0)})

        return result[:6] if result else None

    except Exception as e:
        print(f"   ❌ {e}")
        return None


# ============================================================
# 4. --plan
# ============================================================

def cmd_plan():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    ensure_tables(cursor)

    total = cursor.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    tagged = cursor.execute(
        "SELECT COUNT(DISTINCT resource_id) FROM resource_tags"
    ).fetchone()[0]
    untagged = total - tagged

    tag_count = cursor.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    conn.close()

    print()
    print("=" * 50)
    print("  ai_tag_generator — Plan")
    print("=" * 50)
    print(f"  Total resources:    {total}")
    print(f"  Already tagged:     {tagged}")
    print(f"  Needs tagging:      {untagged}")
    print(f"  Unique tags so far: {tag_count}")
    print()
    if untagged > 0:
        print(f"  Run: python3 ai_tag_generator.py --limit 10")
        print(f"       python3 ai_tag_generator.py")
    else:
        print(f"  ✅ All resources tagged.")
    print()


# ============================================================
# 5. 主流程
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="BigPRC ai_tag_generator — AI tag extractor")
    parser.add_argument("--plan", action="store_true", help="Show pending counts")
    parser.add_argument("--limit", type=int, default=None, help="Max resources to tag")
    parser.add_argument("--force", action="store_true", help="Re-tag all, clear existing tags")
    args = parser.parse_args()

    if args.plan:
        cmd_plan()
        return

    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()
    ensure_tables(cursor)

    if args.force:
        cursor.execute("DELETE FROM resource_tags")
        cursor.execute("DELETE FROM tags")
        conn.commit()
        print("🧹 Cleared existing tags")

    resources = get_untagged(cursor, force=args.force, limit=args.limit)

    if not resources:
        print("✅ All resources already tagged.")
        conn.close()
        return

    print(f"🏷️  Extracting tags for {len(resources)} resources")
    print()

    ok, fail = 0, 0
    for idx, row in enumerate(resources, 1):
        res_id, title, cat, kws, summary, seo_desc = row
        print(f"[{idx}/{len(resources)}] {res_id}  {title[:50]}")

        tags = extract_tags(title, cat, kws, summary, seo_desc)
        if tags:
            save_tags(cursor, res_id, tags)
            conn.commit()
            ok += 1
            names = ", ".join(t["name"] for t in tags[:5])
            print(f"   ✅ {names}")
        else:
            fail += 1

        if idx % 20 == 0:
            conn.commit()
        time.sleep(0.3)

    conn.commit()

    # Stats
    tag_count = cursor.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
    conn.close()

    print()
    print("=" * 50)
    print(f"  Tags: ✅ {ok} gen  ❌ {fail} fail  |  {tag_count} unique tags")
    print("=" * 50)


if __name__ == "__main__":
    main()

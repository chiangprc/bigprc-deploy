#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BigPRC collection_generator.py — Tag 驱动的自动专题生成器 (P1-3)

基于高频标签组合自动创建 Collections，填充 resource_collections 关联表。

用法:
  python3 collection_generator.py --plan       # 预览即将生成的专题
  python3 collection_generator.py              # 生成专题 + 填充关联
  python3 collection_generator.py --rebuild    # 清空重建所有专题

Config: 读取 /root/scripts/.env (DB_FILE)
"""

import os
import sys
import json
import sqlite3
import time
from dotenv import load_dotenv
from openai import OpenAI

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
DB_FILE = os.getenv("DB_FILE")
API_BASE_URL = os.getenv("API_BASE_URL")
API_KEY      = os.getenv("API_KEY")

if not DB_FILE:
    print("❌ DB_FILE not set")
    sys.exit(1)

client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL, timeout=30.0) if API_KEY else None

# ============================================================
# 专题定义: tag 组合规则 → collection
# ============================================================

COLLECTION_DEFS = [
    # 影视纪录片
    {"id":"bbc-nature","title":"BBC 自然纪录片","tags":["BBC","纪录片"],"cats":["自然科学","历史文化"],"featured":1},
    {"id":"bbc-history","title":"BBC 历史纪录片","tags":["BBC","历史"],"cats":["历史文化"],"featured":1},
    {"id":"discovery-science","title":"Discovery 科学探索","tags":["Discovery","纪录片"],"cats":["自然科学"],"featured":1},
    {"id":"natgeo-nature","title":"国家地理 自然奇观","tags":["国家地理","自然"],"cats":["自然科学","旅行地理"],"featured":1},
    {"id":"imax-doc","title":"IMAX 巨幕纪录片","tags":["IMAX","纪录片"],"cats":["自然科学","历史文化","旅行地理"],"featured":1},
    {"id":"space-universe","title":"宇宙探索","tags":["宇宙"],"cats":["自然科学"],"featured":1},
    {"id":"ocean-wildlife","title":"海洋与野生动物","tags":["海洋","动物"],"cats":["自然科学"],"featured":0},
    {"id":"war-history","title":"战争与历史","tags":["战争","历史"],"cats":["历史文化"],"featured":0},

    # 道家文化
    {"id":"taoist-classics","title":"道家经典文献","tags":["道教","古籍"],"cats":["传统文化"],"featured":1},
    {"id":"taoist-rituals","title":"道教符箓科仪","tags":["符箓","符咒","科仪"],"cats":["传统文化"],"featured":0},
    {"id":"taoist-manuscripts","title":"道家手抄孤本","tags":["手抄本","道教"],"cats":["传统文化"],"featured":0},
    {"id":"buddhist-texts","title":"佛教经典文献","tags":["佛教","古籍"],"cats":["传统文化"],"featured":0},

    # 学习资源
    {"id":"english-learning","title":"英语学习资源","tags":["英语","课程"],"cats":["课程学习","儿童教育"],"featured":1},
    {"id":"kids-education","title":"儿童启蒙教育","tags":["儿童","动画"],"cats":["儿童教育"],"featured":1},
    {"id":"stem-courses","title":"STEM 科学课程","tags":["数学","物理","科学","课程"],"cats":["课程学习"],"featured":0},
    {"id":"design-photo","title":"设计与摄影教程","tags":["设计","摄影","课程"],"cats":["设计创意","艺术设计"],"featured":0},

    # 软件工具
    {"id":"android-tools","title":"Android 实用工具","tags":["Android"],"cats":["软件工具"],"min_resources":10,"featured":1},
    {"id":"windows-software","title":"Windows 效率软件","tags":["Windows"],"cats":["软件工具","编程开发"],"min_resources":10,"featured":1},
    {"id":"video-editing","title":"视频剪辑工具包","tags":["视频剪辑"],"cats":["设计创意","课程学习"],"featured":1},
    {"id":"ai-tools","title":"AI 效率工具","tags":["AI","工具"],"cats":["AI技术","软件工具"],"featured":1},

    # 电子书
    {"id":"ebook-collections","title":"经典电子书合集","tags":["电子书"],"cats":["电子书籍"],"min_resources":20,"featured":0},
    {"id":"reference-books","title":"词典与工具书","tags":["词典","电子书"],"cats":["电子书籍"],"featured":0},
]


def ensure_schema(cursor):
    """确保 rule_json / score 列存在."""
    cols = set(r[1] for r in cursor.execute("PRAGMA table_info(collections)").fetchall())
    if "rule_json" not in cols:
        cursor.execute("ALTER TABLE collections ADD COLUMN rule_json TEXT")
    rcols = set(r[1] for r in cursor.execute("PRAGMA table_info(resource_collections)").fetchall())
    if "score" not in rcols:
        cursor.execute("ALTER TABLE resource_collections ADD COLUMN score REAL DEFAULT 0.0")


def populate_collection(cursor, coll_def):
    """根据 tag 规则匹配资源, 填充 resource_collections."""
    cid = coll_def["id"]

    # 构建 WHERE 条件
    tag_conditions = []
    params = []

    for tag in coll_def.get("tags", []):
        tag_conditions.append("EXISTS (SELECT 1 FROM resource_tags rt2 JOIN tags t2 ON rt2.tag_id=t2.id WHERE rt2.resource_id=r.res_id AND t2.name=?)")
        params.append(tag)

    where = " AND ".join(tag_conditions)

    # 可选: 限定 category
    cat_filter = ""
    if coll_def.get("cats"):
        cat_placeholders = ",".join("?" * len(coll_def["cats"]))
        cat_filter = f" AND r.category IN ({cat_placeholders})"
        params.extend(coll_def["cats"])

    params.append(coll_def.get("min_resources", 3))

    query = f"""
        SELECT r.res_id FROM resources r
        WHERE {where}
        {cat_filter}
        GROUP BY r.res_id
        HAVING COUNT(*) >= ?
    """

    resources = cursor.execute(query, params).fetchall()

    if len(resources) < (coll_def.get("min_resources", 3)):
        return 0  # 不满足最小资源数

    count = 0
    for (res_id,) in resources:
        cursor.execute("""
            INSERT OR IGNORE INTO resource_collections (resource_id, collection_id, score)
            VALUES (?, ?, 1.0)
        """, (res_id, cid))
        count += cursor.rowcount

    return count


def generate_intro(cursor, coll_def, resource_count):
    """AI 生成专题简介 + SEO."""
    if not client:
        return

    sample = cursor.execute("""
        SELECT r.title FROM resources r
        JOIN resource_collections rc ON r.res_id = rc.resource_id
        WHERE rc.collection_id=? ORDER BY RANDOM() LIMIT 5
    """, (coll_def["id"],)).fetchall()
    samples = ", ".join(r[0][:40] for r in sample)

    prompt = f"""Write a 2-sentence intro and SEO description for this curated collection.

Title: {coll_def["title"]}
Contains {resource_count} resources. Examples: {samples}

Output JSON:
{{"intro":"...","seo_title":"...","seo_desc":"..."}}

Rules:
- intro: 30-50 chars, what this collection is + why it matters (Chinese)
- seo_title: 10-20 chars, search-friendly title
- seo_desc: 50-100 chars, SEO meta description
- No marketing buzzwords
JSON only."""

    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role":"user","content":prompt}],
            temperature=0.5, max_tokens=300,
            response_format={"type":"json_object"})
        data = json.loads(resp.choices[0].message.content)
        cursor.execute("""
            INSERT OR REPLACE INTO collection_content (collection_id, intro, seo_title, seo_desc)
            VALUES (?,?,?,?)
        """, (coll_def["id"], data.get("intro",""), data.get("seo_title",""), data.get("seo_desc","")))
        print(f"   ✍️  intro: {data.get('intro','')[:50]}")
    except Exception as e:
        print(f"   ⚠️  intro gen skipped: {e}")


def main():
    plan_only = "--plan" in sys.argv
    rebuild = "--rebuild" in sys.argv

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    ensure_schema(cursor)

    if rebuild:
        cursor.execute("DELETE FROM resource_collections")
        cursor.execute("DELETE FROM collection_content")
        cursor.execute("DELETE FROM collections")
        conn.commit()
        print("🧹 Cleared all collections")

    print(f"📚 Generating {len(COLLECTION_DEFS)} collections...")
    print()

    created, skipped, total_resources = 0, 0, 0

    for coll in COLLECTION_DEFS:
        cid = coll["id"]
        title = coll["title"]

        # 计算匹配资源数 (用于 plan)
        tag_list = coll.get("tags", [])
        where_parts = []
        for tag in tag_list:
            where_parts.append("EXISTS (SELECT 1 FROM resource_tags rt2 JOIN tags t2 ON rt2.tag_id=t2.id WHERE rt2.resource_id=r.res_id AND t2.name=?)")
        where_sql = " AND ".join(where_parts)
        params = list(tag_list) + [coll.get("min_resources", 3)]
        match_count = cursor.execute(
            f"SELECT COUNT(DISTINCT r.res_id) FROM resources r WHERE {where_sql}",
            params[:-1]
        ).fetchone()[0]

        if match_count < coll.get("min_resources", 3):
            if plan_only:
                print(f"  ⏭️  {title} — {match_count} resources (min {coll.get('min_resources',3)})")
            skipped += 1
            continue

        if plan_only:
            print(f"  📋 {title} — {match_count} resources")
            created += 1
            total_resources += match_count
            continue

        # UPSERT collection
        cursor.execute("""
            INSERT OR REPLACE INTO collections (id, title, description, rule_json, is_featured, sort_order)
            VALUES (?,?,?,?,?,?)
        """, (cid, title, coll.get("title",""),
              json.dumps({"tags":tag_list,"cats":coll.get("cats",[])}),
              coll.get("featured",0), 0))

        # 填充资源关联
        count = populate_collection(cursor, coll)
        if count > 0:
            print(f"  ✅ {title:24s} — {count} resources")
            # AI 生成简介
            generate_intro(cursor, coll, count)
            conn.commit()
            created += 1
            total_resources += count
        else:
            skipped += 1

        time.sleep(0.3)

    conn.commit()

    # 更新 collection 的 sort_order
    for i, coll in enumerate(COLLECTION_DEFS):
        cursor.execute("UPDATE collections SET sort_order=? WHERE id=?", (i+1, coll["id"]))
    conn.commit()

    # 输出
    print()
    print("=" * 60)
    print(f"  Collections: ✅ {created} created  ⏭️  {skipped} skipped")
    print(f"  Resource links: {total_resources} total")
    print("=" * 60)

    if plan_only and created > 0:
        print("\n  Run without --plan to generate.")

    conn.close()


if __name__ == "__main__":
    main()

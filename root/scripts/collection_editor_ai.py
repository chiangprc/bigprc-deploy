#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BigPRC collection_editor_ai.py — AI 编辑策展内容生成器 (Phase 4.2)

为 16 个专题生成 editor_note / why_collect / audience / highlights，
写入 collection_content 表。

用法:
  python3 collection_editor_ai.py --plan       # 查看待生成专题
  python3 collection_editor_ai.py --limit 1    # 灰度 1 个专题
  python3 collection_editor_ai.py --limit 3    # 灰度 3 个
  python3 collection_editor_ai.py              # 全量 16 个

Config: /root/scripts/.env
"""

import os, sys, json, time, sqlite3
from dotenv import load_dotenv
from openai import OpenAI

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
DB_FILE = os.getenv("DB_FILE")
API_KEY  = os.getenv("API_KEY")
API_BASE = os.getenv("API_BASE_URL")

if not DB_FILE or not API_KEY:
    print("❌ DB_FILE / API_KEY not set")
    sys.exit(1)

client = OpenAI(api_key=API_KEY, base_url=API_BASE, timeout=40.0)
MODEL = "deepseek-chat"


def get_collections(cursor):
    """读取所有有资源的专题及其元数据."""
    return cursor.execute("""
        SELECT c.id, c.title,
               cc.intro, cc.seo_desc,
               (SELECT COUNT(*) FROM resource_collections WHERE collection_id=c.id) AS cnt,
               (SELECT GROUP_CONCAT(r.title, '、') FROM resources r
                JOIN resource_collections rc ON r.res_id=rc.resource_id
                WHERE rc.collection_id=c.id ORDER BY rc.score DESC LIMIT 8) AS samples
        FROM collections c
        LEFT JOIN collection_content cc ON c.id=cc.collection_id
        WHERE c.id IN (SELECT DISTINCT collection_id FROM resource_collections)
        ORDER BY cnt DESC
    """).fetchall()


def generate_editorial(coll_id, title, intro, seo_desc, samples, count):
    """AI 生成编辑策展四字段."""
    sample_str = (samples or "")[:500]
    prompt = f"""You are a curator for BigPRC, a curated digital resource library. Your job is NOT to introduce what these resources are, but to explain WHY they deserve to be collected and preserved long-term.

Collection: {title}
Existing intro: {intro or '(none)'}
Existing description: {seo_desc or '(none)'}
Contains {count} resources. Examples: {sample_str}

Output JSON with four fields. Write in Chinese (中文). Be SPECIFIC and CONCRETE — no generic filler.

1. editor_note (100-150 chars): Editorial perspective. Why did the curator curate this collection? What makes these resources worth gathering together? What is the editorial angle?
   Good: "BBC 自然纪录片几十年来以严谨的科学态度和震撼的影像语言记录地球生态。这个专题不是简单罗列，而是从蓝色星球到绿色星球，梳理出一条理解地球生命系统的策展线索。"
   Bad: "BBC 是非常优秀的纪录片，值得观看。" (too generic)

2. why_collect (80-120 chars): Long-term collecting value. What makes this collection worth saving, revisiting, referencing? What problem does it solve for the user?
   Good: "自然科学学习与科普启蒙的权威影像资料库，适合反复观看、课堂教学和家庭收藏。高清画质和双语字幕使其兼具观赏与语言学习价值。"
   Bad: "非常值得收藏。" (empty)

3. audience (50-80 chars): Who will benefit most? Be specific, not "everyone".
   Good: "自然爱好者、纪录片收藏者、儿童科普启蒙家长、中学地理/生物教师。"
   Bad: "所有人。" (useless)

4. highlights (3-5 items JSON array): What are the standout resources in this collection? Name specific titles from the examples.
   Good: ["《蓝色星球》海洋纪录片标杆", "《地球脉动》系列呈现全球生态奇观", "《绿色星球》以植物视角重新理解自然"]
   Bad: ["资源1", "资源2"]

RULES:
- NEVER use marketing buzzwords: "神器" "必备" "最强" "顶级" "全网第一" "强烈推荐"
- NEVER say "这是一个..." or "本专题收录..." (weak opening)
- For documentary collections: focus on scientific rigor + visual spectacle + educational value
- For software collections: focus on practical utility + efficiency gains + reliability
- For cultural collections (Taoism/Buddhism): focus on scholarly value + rarity + tradition preservation
- Be specific, not enthusiastic. Substance over style.

JSON only:
{{"editor_note":"...","why_collect":"...","audience":"...","highlights":["...","...","..."]}}"""

    try:
        resp = client.chat.completions.create(
            model=MODEL, messages=[{"role":"user","content":prompt}],
            temperature=0.6, max_tokens=800,
            response_format={"type":"json_object"})
        data = json.loads(resp.choices[0].message.content)
        # Validate all 4 fields present
        if all(k in data for k in ["editor_note","why_collect","audience","highlights"]):
            if isinstance(data["highlights"], list) and len(data["highlights"]) >= 2:
                return data
    except Exception as e:
        print(f"   ❌ {e}")
    return None


def main():
    plan_only = "--plan" in sys.argv
    limit = None
    for i, a in enumerate(sys.argv):
        if a == "--limit" and i+1 < len(sys.argv):
            limit = int(sys.argv[i+1])

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    colls = get_collections(cursor)

    if plan_only:
        print(f"📋 {len(colls)} collections pending editorial content:")
        for c in colls:
            print(f"   {c[1]} ({c[4]} resources)")
        conn.close()
        return

    if limit:
        colls = colls[:limit]

    print(f"✍️  Generating editorial content for {len(colls)} collections...\n")
    ok, fail = 0, 0

    for c in colls:
        cid, title, intro, seo_desc, cnt, samples = c
        print(f"[{title}] ", end="", flush=True)

        data = generate_editorial(cid, title, intro, seo_desc, samples, cnt)
        if data:
            cursor.execute("""
                UPDATE collection_content
                SET editor_note=?, why_collect=?, audience=?, highlights=?
                WHERE collection_id=?
            """, (
                data["editor_note"],
                data["why_collect"],
                data["audience"],
                json.dumps(data["highlights"], ensure_ascii=False),
                cid
            ))
            conn.commit()
            ok += 1
            print(f"✅ {len(data['highlights'])} highlights")
        else:
            fail += 1
        time.sleep(0.4)

    conn.commit(); conn.close()
    print(f"\n✅ {ok} generated  ❌ {fail} failed")


if __name__ == "__main__":
    main()

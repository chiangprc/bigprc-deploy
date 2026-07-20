#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BigPRC collection_faq.py — AI 生成专题 FAQ (Phase 3.1)

读取 collection + collection_content + 资源列表，生成 3-5 组
结构化 Q&A 写入 collection_content.faq_json。

用法:
  python3 collection_faq.py --plan        # 显示待生成清单
  python3 collection_faq.py --limit 3     # 灰度 3 个专题
  python3 collection_faq.py               # 全量生成

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

client = OpenAI(api_key=API_KEY, base_url=API_BASE, timeout=30.0)
MODEL = "deepseek-chat"


def get_collections(cursor):
    """读取所有有资源的专题."""
    return cursor.execute("""
        SELECT c.id, c.title, c.description, cc.intro,
               (SELECT COUNT(*) FROM resource_collections WHERE collection_id=c.id) AS cnt,
               (SELECT GROUP_CONCAT(r.title, '|') FROM resources r
                JOIN resource_collections rc ON r.res_id=rc.resource_id
                WHERE rc.collection_id=c.id ORDER BY rc.score DESC LIMIT 8) AS samples
        FROM collections c
        LEFT JOIN collection_content cc ON c.id=cc.collection_id
        WHERE c.id IN (SELECT DISTINCT collection_id FROM resource_collections)
        ORDER BY cnt DESC
    """).fetchall()


def generate_faq(coll_id, title, intro, samples, count):
    """AI 生成 3-5 组 Q&A."""
    sample_list = (samples or "").replace("|", "、")
    prompt = f"""You are a curator for a digital resource library. Write 3-5 FAQ Q&A pairs for this curated collection.

Collection: {title}
Description: {intro or ''}
Contains {count} resources. Examples: {sample_list[:300]}

Output JSON array:
[
  {{"q":"What are the best BBC nature documentaries?","a":"Classics include..."}},
  ...
]

Rules:
- Questions should be what real users would search (Chinese): "有哪些经典的...", "...推荐", "适合...吗"
- Answers: 20-60 chars, informative, no marketing, mention 2-3 specific resource names from the samples
- 3-5 pairs, sorted by search relevance
- Write in Chinese (中文)

JSON only:"""

    try:
        resp = client.chat.completions.create(
            model=MODEL, messages=[{"role":"user","content":prompt}],
            temperature=0.5, max_tokens=600,
            response_format={"type":"json_object"})
        data = json.loads(resp.choices[0].message.content)
        faqs = data.get("faq", data) if isinstance(data, dict) else data
        if isinstance(faqs, list) and len(faqs) >= 2:
            return json.dumps(faqs, ensure_ascii=False)
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

    pending = [(c, faq) for c in colls if not (faq := cursor.execute(
        "SELECT faq_json FROM collection_content WHERE collection_id=?", (c[0],)
    ).fetchone()[0])]

    if plan_only:
        print(f"📋 {len(pending)} collections need FAQ:")
        for c, _ in pending:
            print(f"   {c[1]} ({c[4]} resources)")
        conn.close()
        return

    if limit:
        pending = pending[:limit]

    print(f"📝 Generating FAQ for {len(pending)} collections...")
    ok, fail = 0, 0
    for c, _ in pending:
        cid, title, desc, intro, cnt, samples = c
        print(f"  [{title}] ", end="", flush=True)
        faq = generate_faq(cid, title, intro, samples, cnt)
        if faq:
            cursor.execute("UPDATE collection_content SET faq_json=? WHERE collection_id=?", (faq, cid))
            conn.commit()
            print(f"✅ {len(json.loads(faq))} Q&As")
            ok += 1
        else:
            print("❌")
            fail += 1
        time.sleep(0.3)

    conn.commit(); conn.close()
    print(f"\n✅ {ok} generated  ❌ {fail} failed")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BigPRC collection_editor_ai.py — AI 编辑策展内容生成器 (Phase 9.1B)

Two modes, fully decoupled:

  --content    Generates: intro, seo_title, seo_desc, faq_json
               Auto-publish. Batch audit. Low risk.

  --editorial  Generates: editor_note, why_collect, audience, highlights
               Draft only. Per-field human approval required. High risk.

Usage:
  python3 collection_editor_ai.py --content                   # auto-publish SEO
  python3 collection_editor_ai.py --content bbc-nature        # single collection
  python3 collection_editor_ai.py --content --force           # overwrite existing

  python3 collection_editor_ai.py --editorial                 # draft editorial
  python3 collection_editor_ai.py --editorial bbc-nature     # single collection
  python3 collection_editor_ai.py --editorial --force         # overwrite existing

  python3 collection_editor_ai.py --editorial bbc-nature --dry-run  # preview only

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

# ============================================================
# Shared helpers
# ============================================================

def get_collections(cursor, target_id=None):
    """读取所有有资源的专题, 或指定单个."""
    where = "AND c.id = ?" if target_id else ""
    params = (target_id,) if target_id else ()
    return cursor.execute(f"""
        SELECT c.id, c.title,
               COALESCE(cc.intro,'') AS intro, COALESCE(cc.seo_desc,'') AS seo_desc,
               (SELECT COUNT(*) FROM resource_collections WHERE collection_id=c.id) AS cnt,
               (SELECT GROUP_CONCAT(r.title, '、') FROM resources r
                JOIN resource_collections rc ON r.res_id=rc.resource_id
                WHERE rc.collection_id=c.id ORDER BY rc.score DESC LIMIT 8) AS samples,
               COALESCE(cc.editor_note,'') AS editor_note,
               COALESCE(cc.why_collect,'') AS why_collect,
               COALESCE(cc.audience,'') AS audience,
               COALESCE(cc.highlights,'') AS highlights
        FROM collections c
        LEFT JOIN collection_content cc ON c.id=cc.collection_id
        WHERE c.id IN (SELECT DISTINCT collection_id FROM resource_collections)
        {where}
        ORDER BY cnt DESC
    """, params).fetchall()


def ai_call(prompt, temperature=0.6, max_tokens=800):
    """Call AI with retry."""
    try:
        resp = client.chat.completions.create(
            model=MODEL, messages=[{"role":"user","content":prompt}],
            temperature=temperature, max_tokens=max_tokens,
            response_format={"type":"json_object"})
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"   ❌ {e}")
        return None


# ============================================================
# --content mode: intro, seo_title, seo_desc, faq_json
# ============================================================

def generate_content(title, intro, seo_desc, samples, count):
    """Generate SEO/info content. Auto-publish. Low risk."""
    sample_str = (samples or "")[:400]
    prompt = f"""You are a content writer for BigPRC, a curated digital resource library.

Collection: {title}
Description: {seo_desc or '(none)'}
Contains {count} resources. Examples: {sample_str}

Output JSON with four fields. Write in Chinese (中文).

1. intro (30-50 chars): What is this collection? Factual overview.
2. seo_title (10-25 chars): Search-friendly title.
3. seo_desc (50-100 chars): SEO meta description.
4. faq_json: 3-5 Q&A pairs as JSON array [{{"q":"...","a":"..."}}].
   Questions: search queries real users would ask.
   Answers: 20-60 chars, informative, mention specific resource names.

Rules:
- Be factual, not enthusiastic
- No marketing words: "神器" "必备" "最强" "全网第一"
- FAQ answers: specific + useful, not generic

JSON only:
{{"intro":"...","seo_title":"...","seo_desc":"...","faq_json":[{{"q":"...","a":"..."}}]}}"""

    data = ai_call(prompt, temperature=0.5, max_tokens=800)
    if data and all(k in data for k in ["intro","seo_title","seo_desc","faq_json"]):
        if isinstance(data["faq_json"], list) and len(data["faq_json"]) >= 2:
            return data
    return None


# ============================================================
# --editorial mode: editor_note, why_collect, audience, highlights
# ============================================================

def generate_editorial(title, seo_desc, samples, count):
    """Generate editorial content. Draft only. High risk. Human approval required.

    Uses prompts from docs/EDITORIAL_PROMPTS.md (Phase 9.1A).
    """
    sample_str = (samples or "")[:500]

    # --- editor_note ---
    prompt_en = f"""You are an editorial curator for BigPRC, a curated digital resource library.
Your writing style: knowledgeable friend making a recommendation.
Not marketing. Not encyclopedia. Not SEO.

Collection: {title}
Description: {seo_desc or '(none)'}
Contains {count} resources. Examples: {sample_str}

Write an editor_note (100-200 Chinese characters, 2-3 sentences):

Sentence 1: What makes this collection special? Express curatorial judgment.
Sentence 2: What specific value does it provide? Be concrete.
Sentence 3 (optional): Who is it for or how to use it.

Rules:
- Reference actual resource names from the samples if they support your point
- Use "从...到..." structure if the collection spans a range
- Never say "这是一个", "值得收藏", "非常优秀" -- these are filler
- Never use "神器", "必备", "最强", "全网第一"
- Write like you're telling a friend why they should care

JSON only:
{{"editor_note":"..."}}"""

    # --- why_collect ---
    prompt_wc = f"""You are an editorial curator for BigPRC.

Collection: {title}
Description: {seo_desc or '(none)'}

Write one sentence (<=50 Chinese characters) explaining why BigPRC created this collection.
This is the curatorial rationale -- not what's in it, but why it exists.

Good: "为自然爱好者提供BBC纪录片的系统收藏与高品质影像资料库"
Bad:  "收录了大量BBC纪录片" (just restating the intro)

Rules:
- One sentence only
- Express motivation, not content
- No marketing words

JSON only:
{{"why_collect":"..."}}"""

    # --- audience ---
    prompt_au = f"""You are an editorial curator for BigPRC.

Collection: {title}
Description: {seo_desc or '(none)'}
Examples: {sample_str}

List 3-5 target audience segments for this collection.
Format: semicolon-separated short labels. Each 2-8 Chinese characters.

Good: "自然爱好者；纪录片收藏者；儿童科普启蒙家长；中学地理/生物教师"
Bad:  "所有人；对纪录片感兴趣的人" (too vague)

Rules:
- Be specific. Think about who would actually use this
- Use descriptive labels, not demographics
- Semicolon-separated, no trailing semicolon
- 3-5 segments total

JSON only:
{{"audience":"..."}}"""

    # --- highlights ---
    prompt_hl = f"""You are an editorial curator for BigPRC.

Collection: {title}
Description: {seo_desc or '(none)'}
Contains {count} resources. Examples: {sample_str}

Write 3-5 collection highlights. Each highlight is 15-30 Chinese characters.
Output as a JSON array of strings.

Good:
["《蓝色星球》海洋纪录片标杆之作","《地球脉动》系列：全球生态奇观","中文字幕 + 高清画质，适合全年龄"]

Bad:
["收录了315部纪录片" (just restating data),"非常值得收藏" (empty praise)]

Rules:
- Reference actual resource names from the samples
- Mix specific titles with thematic observations
- Do NOT repeat the intro or description
- No marketing language

JSON only:
{{"highlights":["...","..."]}}"""

    results = {}
    for name, prompt in [("editor_note", prompt_en), ("why_collect", prompt_wc),
                           ("audience", prompt_au), ("highlights", prompt_hl)]:
        time.sleep(0.2)
        data = ai_call(prompt, temperature=0.7, max_tokens=400)
        if data and name in data:
            results[name] = data[name]
        else:
            print(f"   ⚠️  {name} failed")
            return None
    return results


# ============================================================
# Main
# ============================================================

def main():
    mode = None           # "content" or "editorial"
    target_id = None      # single collection slug
    force = False
    dry_run = False
    limit = None

    args = sys.argv[1:]
    # Separate flags from positional arg (collection ID)
    flags = [a for a in args if a.startswith("--")]
    positional = [a for a in args if not a.startswith("--")]
    if "--content" in flags: mode = "content"
    if "--editorial" in flags: mode = "editorial"
    if "--force" in flags: force = True
    if "--dry-run" in flags: dry_run = True
    for j, a in enumerate(flags):
        if a == "--limit" and j+1 < len(flags):
            try: limit = int(flags[j+1])
            except ValueError: pass
    if positional: target_id = positional[0]

    if not mode:
        print("Usage:")
        print("  python3 collection_editor_ai.py --content [id] [--force] [--limit N]")
        print("  python3 collection_editor_ai.py --editorial [id] [--force] [--dry-run] [--limit N]")
        sys.exit(1)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    colls = get_collections(cursor, target_id)

    if not colls:
        print(f"❌ No collections found" + (f" for '{target_id}'" if target_id else ""))
        conn.close()
        sys.exit(1)

    if limit:
        colls = colls[:limit]

    label = "SEO Content" if mode == "content" else "Editorial"
    if dry_run: label += " (DRY RUN)"
    print(f"✍️  Generating {label} for {len(colls)} collections...\n")

    ok, skip, fail = 0, 0, 0

    for c in colls:
        cid, title, intro, seo_desc, cnt, samples, en, wc, au, hl = c

        # Skip check
        if mode == "content":
            has_all = intro and seo_desc
        else:
            has_all = en and wc and au and hl

        if has_all and not force:
            print(f"[{title}] ⏭️  already exists")
            skip += 1
            continue

        print(f"[{title}] ", end="", flush=True)

        if mode == "content":
            data = generate_content(title, intro, seo_desc, samples, cnt)
            if data:
                if not dry_run:
                    cursor.execute("""
                        UPDATE collection_content
                        SET intro=?, seo_title=?, seo_desc=?, faq_json=?
                        WHERE collection_id=?
                    """, (data["intro"], data["seo_title"], data["seo_desc"],
                          json.dumps(data["faq_json"], ensure_ascii=False), cid))
                    conn.commit()
                ok += 1
                print(f"✅ intro={data['intro'][:40]}")
                if dry_run:
                    print(f"   seo_title: {data['seo_title']}")
                    print(f"   seo_desc:  {data['seo_desc'][:80]}")
                    print(f"   faq:       {len(data['faq_json'])} Q&A")
            else:
                fail += 1
        else:  # editorial
            data = generate_editorial(title, seo_desc, samples, cnt)
            if data and len(data) >= 4:
                if not dry_run:
                    cursor.execute("""
                        UPDATE collection_content
                        SET editor_note=?, why_collect=?, audience=?, highlights=?
                        WHERE collection_id=?
                    """, (data["editor_note"], data["why_collect"], data["audience"],
                          json.dumps(data["highlights"], ensure_ascii=False), cid))
                    conn.commit()
                ok += 1
                if dry_run:
                    print(f"   editor_note:  {data['editor_note'][:80]}")
                    print(f"   why_collect:  {data['why_collect']}")
                    print(f"   audience:     {data['audience']}")
                    print(f"   highlights:   {json.dumps(data['highlights'], ensure_ascii=False)[:100]}")
                else:
                    print(f"✅ {len(data['highlights'])} highlights")
            else:
                fail += 1
        time.sleep(0.3)

    if not dry_run:
        conn.commit()
    conn.close()

    print(f"\n✅ {ok} generated  ⏭️  {skip} skipped  ❌ {fail} failed")
    if dry_run:
        print("🧪 DRY RUN — no data written")


if __name__ == "__main__":
    main()

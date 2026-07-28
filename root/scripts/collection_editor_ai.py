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
    """Call AI. For JSON parse failures, return raw text for fallback parsing."""
    try:
        resp = client.chat.completions.create(
            model=MODEL, messages=[{"role":"user","content":prompt}],
            temperature=temperature, max_tokens=max_tokens,
            response_format={"type":"json_object"})
        raw = resp.choices[0].message.content.strip()
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        # JSON mode failed — retry without response_format for raw text
        try:
            resp2 = client.chat.completions.create(
                model=MODEL, messages=[{"role":"user","content":prompt}],
                temperature=temperature, max_tokens=max_tokens)
            raw2 = resp2.choices[0].message.content.strip()
            # Try parsing the fallback response
            try:
                return json.loads(raw2)
            except (json.JSONDecodeError, TypeError):
                # Return raw text in a dict wrapper for parse_highlights fallback
                return {"_raw": raw2}
        except Exception:
            pass
        return None
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

def parse_highlights(raw):
    """Multi-level parser for AI-generated highlights output.

    Returns: (list[str] | None, label: str)
    Level 1: json.loads()
    Level 2: auto-fix common errors then json.loads()
    Level 3: fallback line parser (markdown, numbered, bullets)
    """
    import re

    # Level 1: clean JSON
    if isinstance(raw, list):
        items = [str(x).strip() for x in raw if str(x).strip()]
        if 3 <= len(items) <= 8:
            return items, "JSON"
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                items = [str(x).strip() for x in parsed if str(x).strip()]
                if 3 <= len(items) <= 8:
                    return items, "JSON"
        except (json.JSONDecodeError, TypeError):
            pass

    # Level 2: auto-fix common AI output errors
    if isinstance(raw, str):
        fixed = raw.strip()
        # Remove markdown code fences
        fixed = re.sub(r'^```(?:json)?\s*', '', fixed)
        fixed = re.sub(r'\s*```$', '', fixed)
        # Remove leading/trailing prose ("Here are the highlights:", etc.)
        fixed = re.sub(r'^[^{[]*', '', fixed)
        fixed = re.sub(r'[^}\]]*$', '', fixed)
        # Fix trailing commas
        fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
        # Fix missing commas between items
        fixed = re.sub(r'"\s*\n\s*"', '",\n"', fixed)
        # Fix Chinese quotes
        fixed = fixed.replace('“', '"').replace('”', '"')
        fixed = fixed.replace('‘', "'").replace('’', "'")
        # Remove inline comments
        fixed = re.sub(r'//[^\n]*', '', fixed)
        # Remove empty lines inside arrays
        fixed = re.sub(r'\n\s*\n', '\n', fixed)
        try:
            parsed = json.loads(fixed)
            if isinstance(parsed, list):
                items = [str(x).strip() for x in parsed if str(x).strip()]
                if 3 <= len(items) <= 8:
                    return items, "Auto-fixed JSON"
        except (json.JSONDecodeError, TypeError):
            pass

    # Level 3: Fallback line parser
    if isinstance(raw, str):
        lines = []
        text = raw.strip()
        # Strip JSON remnants
        text = re.sub(r'"?highlights"?\s*:\s*\[', '', text)
        text = re.sub(r'[\[\]{}]', ' ', text)
        # Remove markdown code fences
        text = re.sub(r'^```.*', '', text, flags=re.MULTILINE)
        # Try to extract list items: - item, * item, 1. item, • item
        for line in text.split('\n'):
            line = line.strip()
            # Strip list markers
            cleaned = re.sub(r'^[\-\*\d+\.\s•]+', '', line).strip()
            # Remove surrounding quotes
            cleaned = cleaned.strip('"\'""“”')
            if cleaned and len(cleaned) >= 4:
                lines.append(cleaned)
        if 3 <= len(lines) <= 8:
            return lines, "Fallback line parser"

    return None, "FAILED"


def generate_editorial(title, seo_desc, samples, count):
    """Generate editorial content. Draft only. High risk. Human approval required.

    Uses prompts from docs/EDITORIAL_PROMPTS.md (Phase 9.1A).
    """
    sample_str = (samples or "")[:500]

    # --- editor_note ---
    prompt_en = f"""You are an editorial curator for BigPRC. Write like a knowledgeable friend.
Your writing must sound like it comes from the same editorial team as other BigPRC collections.
Not marketing. Not encyclopedia. Not AI summary. Not product description.

Collection: {title}
Description: {seo_desc or '(none)'}
Contains {count} resources. Examples: {sample_str}

First, infer the collection's domain from its title, description, and examples.
All editorial content MUST stay within this inferred domain. Never reference
content from unrelated domains (e.g. no BBC documentaries in AI tools, no
software in nature documentaries).

Write an editor_note with this structure:
1. Opening judgement — what makes this collection worth curating?
2. Reference 2-3 specific resources from the examples — show, don't just tell.
3. Editorial recommendation — who is this for and what value does it provide?

Character count is a soft guideline; editorial structure is the priority.
- Never say "这是一个", "值得收藏", "非常优秀", "不可错过"
- Never use "神器", "必备", "最强", "全网第一", "禁片", "绝密"
- Use neutral, measured language. Let the content speak for itself.

JSON only:
{{"editor_note":"..."}}"""

    # --- why_collect ---
    prompt_wc = f"""You are an editorial curator for BigPRC.

Collection: {title}
Description: {seo_desc or '(none)'}

Write one sentence explaining WHY BigPRC built this collection.
This is curatorial motivation, not a content summary or SEO description.

Good: "为自然爱好者提供BBC纪录片的系统收藏与高品质影像资料库"
Bad:  "收录了大量BBC纪录片，涵盖动物生态地理科学探索" (too long, too descriptive)

Rules:
- One sentence. Short. Direct.
- Express motivation ("to provide...", "to preserve...", "to help...")
- Do NOT list what's inside. Do NOT use keywords.
- No marketing words.

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

Each highlight MUST contain a real resource title from the examples.
Prefer titles from the sampled list. Never invent resource names.

Good:
["《蓝色星球》海洋纪录片标杆之作","《地球脉动》系列：全球生态奇观","中文字幕 + 高清画质，适合全年龄"]

Bad:
["收录了315部纪录片" (just restating data),"非常值得收藏" (empty praise)]
["ChatGPT教学课程" (if not in the sample list)]

Rules:
- Every highlight references a real resource title from the collection
- Each is a short value statement, not a feature list
- No marketing language
- No invented resource names

JSON only:
{{"highlights":["...","..."]}}"""

    results = {}
    parser_used = None
    hl_raw = None
    for name, prompt in [("editor_note", prompt_en), ("why_collect", prompt_wc),
                           ("audience", prompt_au), ("highlights", prompt_hl)]:
        time.sleep(0.2)
        data = ai_call(prompt, temperature=0.7, max_tokens=400)
        if data and (name in data or "_raw" in data):
            if name == "highlights":
                val = data.get(name) or data.get("_raw","")
                hl_raw = val
                parsed, parser_label = parse_highlights(val)
                if parsed:
                    results[name] = parsed
                    parser_used = parser_label
                else:
                    print(f"   ⚠️  highlights parse failed, raw: {str(val)[:120]}")
                    results[name] = []
                    parser_used = "FAILED"
            else:
                results[name] = data[name]
        else:
            if name != "highlights":
                print(f"   ⚠️  {name} failed")
                return None
            else:
                print(f"   ⚠️  highlights AI call failed")
                results[name] = []
                parser_used = "FAILED"
    if parser_used:
        results["_parser"] = parser_used
    # Return if we have at least the 3 non-highlights fields
    return results if all(k in results for k in ["editor_note","why_collect","audience"]) else None


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

    # Sanity check — if VPS is running old code, this line won't appear
    if target_id:
        print(f"🎯 Target: {target_id}")

    colls = get_collections(cursor, target_id)

    if not colls:
        print(f"❌ No collections found" + (f" for '{target_id}'" if target_id else ""))
        conn.close()
        sys.exit(1)

    if limit:
        colls = colls[:limit]

    label = "SEO Content" if mode == "content" else "Editorial"
    if dry_run: label += " (DRY RUN)"
    print(f"✍️  Generating {label} for {len(colls)} collections...")
    if target_id and len(colls) != 1:
        print(f"   ⚠️  Expected 1 collection for '{target_id}', got {len(colls)}")
    print()

    ok, skip, fail = 0, 0, 0
    parser_stats = {"JSON": 0, "Auto-fixed JSON": 0, "Fallback line parser": 0, "FAILED": 0}

    def has_old(val):
        return bool(val and str(val).strip())

    for c in colls:
        cid, title, intro, seo_desc, cnt, samples, en, wc, au, hl = c

        # Dry-run: always generate and print preview, never skip
        if dry_run:
            print(f"[{title}] 🧪 DRY RUN")
            if has_old(en if mode == "editorial" else intro):
                print(f"   📄 已有内容 (数据库未修改)")
            if mode == "content":
                data = generate_content(title, intro, seo_desc, samples, cnt)
                if data:
                    ok += 1
                    print(f"   ── Preview ──")
                    print(f"   intro:       {data['intro']}")
                    print(f"   seo_title:   {data['seo_title']}")
                    print(f"   seo_desc:    {data['seo_desc'][:80]}")
                    print(f"   faq:         {len(data['faq_json'])} Q&A")
                else:
                    fail += 1
            else:
                data = generate_editorial(title, seo_desc, samples, cnt)
                if data:
                    ok += 1
                    parser = data.pop("_parser", "?")
                    parser_stats[parser] = parser_stats.get(parser, 0) + 1
                    print(f"   ── Preview ──")
                    print(f"   editor_note:  {data.get('editor_note','(missing)')}")
                    print(f"   why_collect:  {data.get('why_collect','(missing)')}")
                    print(f"   audience:     {data.get('audience','(missing)')}")
                    hl = data.get('highlights', [])
                    print(f"   highlights:   {json.dumps(hl, ensure_ascii=False) if hl else '(empty)'}")
                    print(f"   parser:       {parser}")
                else:
                    fail += 1
            print()
            continue

        # Normal mode: skip if exists, unless --force
        if mode == "content":
            has_all = intro and seo_desc
        else:
            has_all = en and wc and au and hl

        if has_all and not force:
            print(f"[{title}] ⏭️  already exists (use --force to overwrite)")
            skip += 1
            continue

        print(f"[{title}] ", end="", flush=True)

        if mode == "content":
            data = generate_content(title, intro, seo_desc, samples, cnt)
            if data:
                cursor.execute("""
                    UPDATE collection_content
                    SET intro=?, seo_title=?, seo_desc=?, faq_json=?
                    WHERE collection_id=?
                """, (data["intro"], data["seo_title"], data["seo_desc"],
                      json.dumps(data["faq_json"], ensure_ascii=False), cid))
                conn.commit()
                ok += 1
                print(f"✅ intro={data['intro'][:40]}...  {len(data['faq_json'])} FAQ")
            else:
                fail += 1
        else:  # editorial
            data = generate_editorial(title, seo_desc, samples, cnt)
            if data:
                parser = data.pop("_parser", "?")
                parser_stats[parser] = parser_stats.get(parser, 0) + 1
                hl_list = data.get("highlights", [])
                cursor.execute("""
                    UPDATE collection_content
                    SET editor_note=?, why_collect=?, audience=?, highlights=?,
                        editorial_status='draft'
                    WHERE collection_id=?
                """, (data["editor_note"], data["why_collect"], data["audience"],
                      json.dumps(hl_list, ensure_ascii=False), cid))
                conn.commit()
                ok += 1
                print(f"✅ {len(hl_list)} highlights  ({parser})")
            else:
                fail += 1
        time.sleep(0.3)

    if not dry_run:
        conn.commit()
    conn.close()

    print(f"\n✅ {ok} generated  ⏭️  {skip} skipped  ❌ {fail} failed")
    if dry_run:
        print("🧪 DRY RUN — no data written")
    if mode == "editorial" and sum(parser_stats.values()) > 0:
        print(f"\n── Parser Summary ──")
        for label in ["JSON", "Auto-fixed JSON", "Fallback line parser", "FAILED"]:
            if parser_stats.get(label, 0) > 0:
                print(f"  {label}: {parser_stats[label]}")


if __name__ == "__main__":
    main()

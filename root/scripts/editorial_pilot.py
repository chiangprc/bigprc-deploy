#!/usr/bin/env python3
"""Phase 10.10.2 — Editorial Generation Engine

Real AI-powered Editor's Take content generation with:
- A/B prompt variants (Differentiation vs Editorial Voice)
- Tier filter (spotlight/core/solid)
- Batch retry on API failure
- Guideline Check before DB write

Usage:
  python3 editorial_pilot.py --generate --tier CORE --limit 20
  python3 editorial_pilot.py --generate --prompt B --tier SOLID --limit 30
  python3 editorial_pilot.py --review
  python3 editorial_pilot.py --publish ID1 ID2 ID3
  python3 editorial_pilot.py --report
  python3 editorial_pilot.py --export /var/www/site/web/admin/data/editorial-pending.json

Rules (from PHASE10_8_1_EDITORIAL_WRITING_GUIDELINE.md):
  - No "非常优秀" "功能强大" "强烈推荐" "值得推荐"
  - No "所有人" in target_audience
  - At least 1 caveat (every resource has limits)
  - At least 1 strength
  - Editor recommendation must be 30+ chars
"""

import os, sys, json, sqlite3, re, time, logging
from datetime import datetime

from db_helper import get_db
DB_FILE = get_db()
API_BASE_URL = os.getenv("API_BASE_URL")
API_KEY = os.getenv("API_KEY")

# ── AI Client Setup ──────────────────────────────────────────
_client = None

def get_client():
    global _client
    if _client is None:
        if not API_KEY:
            print("❌ API_KEY not set in .env")
            sys.exit(1)
        from openai import OpenAI
        _client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL, timeout=90.0)
    return _client

FALLBACK_MODELS = ["gpt-4o", "gpt-4o-mini"]
ERROR_LOG = "/root/scripts/editorial_generation_errors.log"
logging.basicConfig(filename=str(ERROR_LOG), level=logging.WARNING,
                    format='%(asctime)s %(message)s')

# ── Guideline Check ──────────────────────────────────────────
FORBIDDEN_PHRASES = [
    "非常优秀", "功能强大", "强烈推荐", "值得推荐",
    "必备", "神器", "全网最全", "最好用",
]

def guideline_check(rec, audience, strengths, caveats):
    """Returns (passed: bool, issues: list[str])"""
    issues = []
    text = f"{rec} {audience}"

    for phrase in FORBIDDEN_PHRASES:
        if phrase in text:
            issues.append(f"Forbidden phrase: '{phrase}'")

    if "所有人" in audience or "每个人" in audience or "用户都适合" in audience:
        issues.append("target_audience too generic (contains '所有人/每个人')")

    if len(rec.strip()) < 30:
        issues.append(f"Recommendation too short ({len(rec)} chars, need 30+)")

    if len(strengths) == 0:
        issues.append("No strengths provided")

    if len(caveats) == 0:
        issues.append("No caveats provided (every resource has limits)")

    return (len(issues) == 0, issues)


# ── A/B Prompt Variants ──────────────────────────────────────
PROMPT_A = """你是 BigPRC 的数字资源策展编辑。你的任务是帮助用户判断一个资源是否适合他们。
你的重点是帮助用户理解：这个资源与其他选择有什么不同，为什么这个版本值得收藏。

资源信息：
名称: {title}
类型: {category}
大小: {file_size}
平台: {platform}
版本: {version}
所属专题: {collections}
现有描述: {seo_desc}

请输出 JSON：
{{
  "editor_recommendation": "1-3 句，告诉用户为什么这个资源值得花时间。必须包含与其他选择相比的特点。如果没有其他版本，说明为什么这个资源稀缺。",
  "target_audience": "从以下类型至少选一种并具体化：零基础入门 / 有基础进阶 / 专业从业者 / 学生 / 内容创作者 / 开发者 / 家庭用户 / 教育者。禁止写'所有人'。",
  "strengths": ["+ 具体可验证优势1", "+ 具体可验证优势2", "+ 具体可验证优势3"],
  "caveats": ["· 真实限制1", "· 真实限制2"]
}}

禁止使用这些词：非常优秀、功能强大、强烈推荐、值得推荐、必备、神器、全网最全、最好用"""

PROMPT_B = """你是 BigPRC 的资深数字资源策展编辑。你在为读者写推荐理由。
你的重点是让推荐读起来像一个真正了解这个领域的编辑在说话——有判断、有取舍、有态度。

资源信息：
名称: {title}
类型: {category}
大小: {file_size}
平台: {platform}
版本: {version}
所属专题: {collections}
现有描述: {seo_desc}

请用编辑的口吻输出 JSON：
{{
  "editor_recommendation": "像一个编辑在向朋友推荐——不夸张，不推销，只是告诉你为什么他选了这一个。1-3句。",
  "target_audience": "写具体的用户画像，不要写'适合所有人'。想想谁会真正需要这个？从零基础/进阶/专业/学生/创作者/开发者/家庭/教育者中选择。",
  "strengths": ["+ 优势1（用具体的、可验证的事实）", "+ 优势2", "+ 优势3"],
  "caveats": ["· 真实的使用限制（不要编造，但也不要省略）", "· 限制2"]
}}

记住：你是编辑，不是销售。你的读者信任你，因为他们知道你会说真话。"""


# ── AI Generation ────────────────────────────────────────────
def call_ai(prompt):
    """Call AI API with fallback chain. Returns parsed dict or None."""
    client = get_client()

    for model in FALLBACK_MODELS:
        # Attempt 1: JSON mode
        try:
            print(f"   [{model}] ", end="", flush=True)
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1200,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content.strip()
            parsed = json.loads(raw)
            print("✅")
            return parsed
        except (json.JSONDecodeError, TypeError):
            print("retry...", end=" ", flush=True)
            # Attempt 2: no JSON mode
            try:
                resp2 = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=1200,
                )
                raw2 = resp2.choices[0].message.content.strip()
                parsed2 = json.loads(raw2)
                print("✅")
                return parsed2
            except Exception:
                pass
        except Exception as e:
            print(f"err ({e})", end=" ", flush=True)
            continue

    print("❌ all models failed")
    return None


def generate_editorial(resource, prompt_variant="A"):
    """Generate Editor's Take content using AI.
    Returns dict with editorial fields, or None on failure."""
    template = PROMPT_A if prompt_variant == "A" else PROMPT_B
    prompt = template.format(
        title=resource.get("title", ""),
        category=resource.get("category", ""),
        file_size=resource.get("file_size", "") or resource.get("size", ""),
        platform=resource.get("platform", ""),
        version=resource.get("version", ""),
        collections=resource.get("collections", "") or resource.get("coll_titles", ""),
        seo_desc=(resource.get("seo_desc", "") or "")[:300],
    )
    result = call_ai(prompt)
    if not result:
        return None

    # Normalize output
    return {
        "editor_recommendation": str(result.get("editor_recommendation", "")),
        "target_audience": str(result.get("target_audience", "")),
        "strengths": result.get("strengths", []) if isinstance(result.get("strengths"), list) else [],
        "caveats": result.get("caveats", []) if isinstance(result.get("caveats"), list) else [],
        "ai_model": FALLBACK_MODELS[0],
    }


# ── Database Operations ──────────────────────────────────────
def get_pilot_resources(conn, limit=50, tier=None, force=False):
    """Select resources for editorial generation.
    tier: 'spotlight', 'core', 'solid' (None = all)
    force: if True, include rejected resources for regeneration."""
    cur = conn.cursor()
    where = "WHERE (r.editorial_status IS NULL"
    if force:
        where += " OR r.editorial_status = 'rejected'"
    where += ")"

    tier_clause = ""
    if tier == 'spotlight':
        where += " AND rc.spotlight = 1"
    elif tier == 'core':
        where += " AND c.quality = 'CORE'"
        tier_clause = ""
    elif tier == 'solid':
        where += " AND c.quality IN ('CORE', 'SOLID')"

    query = f"""
        SELECT r.id, r.title, r.category, r.file_size, r.platform,
               r.version, r.seo_desc,
               GROUP_CONCAT(c.title, ', ') as coll_titles
        FROM resources r
        LEFT JOIN resource_collections rc ON r.id = rc.resource_id
        LEFT JOIN collections c ON rc.collection_id = c.id
        {where}
        GROUP BY r.id
        ORDER BY
            CASE WHEN rc.spotlight = 1 THEN 0 ELSE 1 END,
            CASE WHEN c.quality = 'CORE' THEN 0
                 WHEN c.quality = 'SOLID' THEN 1
                 ELSE 2 END,
            RANDOM()
        LIMIT ?
    """
    cur.execute(query, (limit,))
    return cur.fetchall()


def insert_editorial(conn, res_id, data, dry_run=False):
    """Write editorial content to database. Only if editorial_status IS NULL."""
    cur = conn.cursor()
    cur.execute("SELECT editorial_status FROM resources WHERE id=?", (res_id,))
    row = cur.fetchone()
    if row and row[0] is not None:
        return False, "Already has editorial content"

    if dry_run:
        return True, "DRY-RUN: would write"

    cur.execute("""
        UPDATE resources SET
            editor_recommendation = ?,
            target_audience = ?,
            strengths = ?,
            caveats = ?,
            editorial_status = 'draft',
            generated_at = ?,
            ai_model = ?
        WHERE id = ?
    """, (
        data["editor_recommendation"],
        data["target_audience"],
        json.dumps(data["strengths"], ensure_ascii=False),
        json.dumps(data["caveats"], ensure_ascii=False),
        datetime.now().isoformat(),
        data.get("ai_model", "unknown"),
        res_id,
    ))
    conn.commit()
    return True, "Written (draft)"


def publish_editorial(conn, res_id):
    """Set status to published (after human review)."""
    cur = conn.cursor()
    cur.execute("SELECT editorial_status FROM resources WHERE id=?", (res_id,))
    row = cur.fetchone()
    if not row or row[0] is None:
        return False, "No editorial content to publish"
    if row[0] == 'published':
        return False, "Already published"

    cur.execute("""
        UPDATE resources SET
            editorial_status = 'published',
            reviewed_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), res_id))
    conn.commit()
    return True, "Published"


def pilot_report(conn):
    """Generate pilot statistics."""
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN editorial_status = 'draft' THEN 1 ELSE 0 END) as drafts,
            SUM(CASE WHEN editorial_status = 'reviewed' THEN 1 ELSE 0 END) as reviewed,
            SUM(CASE WHEN editorial_status = 'published' THEN 1 ELSE 0 END) as published,
            AVG(LENGTH(editor_recommendation)) as avg_rec_len,
            AVG(LENGTH(target_audience)) as avg_aud_len
        FROM resources
        WHERE editorial_status IS NOT NULL
    """)
    row = cur.fetchone()
    print(f"\n=== Editorial Pilot Report ===")
    print(f"Total with editorial:  {row[0] or 0}")
    print(f"  Draft:              {row[1] or 0}")
    print(f"  Reviewed:           {row[2] or 0}")
    print(f"  Published:          {row[3] or 0}")
    print(f"  Avg rec length:     {row[4] or 0:.0f} chars")
    print(f"  Avg audience length: {row[5] or 0:.0f} chars")
    print()

    # Strengths/caveats counts
    cur.execute("SELECT strengths, caveats FROM resources WHERE editorial_status IS NOT NULL")
    s_counts, c_counts = [], []
    for s, c in cur.fetchall():
        try:
            s_counts.append(len(json.loads(s)) if s else 0)
            c_counts.append(len(json.loads(c)) if c else 0)
        except json.JSONDecodeError:
            pass
    if s_counts:
        print(f"  Avg strengths: {sum(s_counts)/len(s_counts):.1f}")
        print(f"  Avg caveats:   {sum(c_counts)/len(c_counts):.1f}")


# ── Production Metrics ───────────────────────────────────────
def production_metrics(conn):
    """Print production dashboard for editorial pipeline."""
    cur = conn.cursor()

    # Generation stats
    cur.execute("""
        SELECT
            COUNT(*) as total_gen,
            SUM(CASE WHEN editorial_status = 'draft' THEN 1 ELSE 0 END) as drafts,
            SUM(CASE WHEN editorial_status = 'reviewed' THEN 1 ELSE 0 END) as reviewed,
            SUM(CASE WHEN editorial_status = 'published' THEN 1 ELSE 0 END) as published,
            SUM(CASE WHEN editorial_status = 'rejected' THEN 1 ELSE 0 END) as rejected,
            AVG(LENGTH(editor_recommendation)) as avg_rec_len,
            AVG(LENGTH(target_audience)) as avg_aud_len
        FROM resources
        WHERE editorial_status IS NOT NULL
    """)
    r = cur.fetchone()

    # Model usage
    cur.execute("""
        SELECT ai_model, COUNT(*) as cnt
        FROM resources
        WHERE ai_model IS NOT NULL
        GROUP BY ai_model ORDER BY cnt DESC
    """)
    models = cur.fetchall()

    # Strengths/caveats averages
    cur.execute("SELECT strengths, caveats FROM resources WHERE editorial_status IS NOT NULL")
    s_lens, c_lens = [], []
    for s, c in cur.fetchall():
        try:
            s_lens.append(len(json.loads(s)) if s else 0)
            c_lens.append(len(json.loads(c)) if c else 0)
        except json.JSONDecodeError:
            pass

    print("\n=== Editorial Production Metrics ===")
    print(f"Total generated:     {r['total_gen'] or 0}")
    print(f"  Draft:             {r['drafts'] or 0}")
    print(f"  Reviewed:          {r['reviewed'] or 0}")
    print(f"  Published:         {r['published'] or 0}")
    print(f"  Rejected:          {r['rejected'] or 0}")
    if r['total_gen']:
        reject_rate = (r['rejected'] or 0) / r['total_gen'] * 100
        publish_rate = (r['published'] or 0) / r['total_gen'] * 100
        print(f"  Publish rate:      {publish_rate:.0f}%")
        print(f"  Reject rate:       {reject_rate:.0f}%")
    print(f"Avg rec length:      {r['avg_rec_len'] or 0:.0f} chars")
    print(f"Avg audience length: {r['avg_aud_len'] or 0:.0f} chars")
    if s_lens:
        print(f"Avg strengths:       {sum(s_lens)/len(s_lens):.1f}")
        print(f"Avg caveats:         {sum(c_lens)/len(c_lens):.1f}")
    if models:
        print(f"Model usage:")
        for m, c in models:
            print(f"  {m}: {c}")
    print()

    # Generation times
    cur.execute("""
        SELECT generated_at, reviewed_at
        FROM resources
        WHERE generated_at IS NOT NULL AND reviewed_at IS NOT NULL
        LIMIT 20
    """)
    # Simple pass/fail thresholds
    checks = []
    if (r['published'] or 0) / max(r['total_gen'] or 1, 1) < 0.5:
        checks.append("⚠ Publish rate < 50%")
    if (r['rejected'] or 0) / max(r['total_gen'] or 1, 1) > 0.1:
        checks.append("⚠ Reject rate > 10%")
    if (r['avg_rec_len'] or 0) < 40:
        checks.append("⚠ Avg recommendation < 40 chars (too short)")
    if s_lens and sum(s_lens)/len(s_lens) < 2.0:
        checks.append("⚠ Avg strengths < 2.0")
    if c_lens and sum(c_lens)/len(c_lens) < 1.0:
        checks.append("⚠ Avg caveats < 1.0")

    if checks:
        print("Quality Alerts:")
        for c in checks:
            print(f"  {c}")
    else:
        print("✅ All quality thresholds met.")

    return {
        "total": r['total_gen'] or 0,
        "published": r['published'] or 0,
        "rejected": r['rejected'] or 0,
        "publish_rate": (r['published'] or 0) / max(r['total_gen'] or 1, 1),
        "reject_rate": (r['rejected'] or 0) / max(r['total_gen'] or 1, 1),
        "avg_rec_len": r['avg_rec_len'] or 0,
        "avg_strengths": sum(s_lens)/len(s_lens) if s_lens else 0,
        "avg_caveats": sum(c_lens)/len(c_lens) if c_lens else 0,
    }


# ── Export for Admin UI ──────────────────────────────────────
def export_review_data(conn, out_path):
    """Export pending/reviewed editorial data for admin UI consumption."""
    cur = conn.cursor()
    cur.execute("""
        SELECT r.id, r.title, r.category,
               r.editor_recommendation, r.target_audience,
               r.strengths, r.caveats,
               r.editorial_status, r.generated_at, r.reviewed_at,
               r.ai_model,
               GROUP_CONCAT(c.title, ', ') as collections
        FROM resources r
        LEFT JOIN resource_collections rc ON r.id = rc.resource_id
        LEFT JOIN collections c ON rc.collection_id = c.id
        WHERE r.editorial_status IN ('draft', 'reviewed')
        GROUP BY r.id
        ORDER BY
            CASE r.editorial_status WHEN 'draft' THEN 0 ELSE 1 END,
            r.generated_at DESC
    """)
    rows = []
    for r in cur.fetchall():
        row = dict(r)
        # Parse JSON arrays
        for field in ['strengths', 'caveats']:
            try:
                row[field] = json.loads(row[field]) if row[field] else []
            except json.JSONDecodeError:
                row[field] = []
        rows.append(row)

    data = {
        "generated_at": datetime.now().isoformat(),
        "total": len(rows),
        "drafts": sum(1 for r in rows if r['editorial_status'] == 'draft'),
        "reviewed": sum(1 for r in rows if r['editorial_status'] == 'reviewed'),
        "items": rows,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Exported {len(rows)} items → {out_path}")


# ── CLI ──────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Editorial Content Pilot")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--generate", action="store_true", help="Generate and write drafts")
    parser.add_argument("--tier", type=str, choices=["spotlight","core","solid"], help="Filter by quality tier")
    parser.add_argument("--limit", type=int, default=50, help="Max resources to generate (default 50)")
    parser.add_argument("--prompt", type=str, choices=["A","B"], default="A", help="Prompt variant: A=Differentiation, B=Editorial Voice")
    parser.add_argument("--force", action="store_true", help="Regenerate rejected resources")
    parser.add_argument("--review", action="store_true", help="List drafts awaiting review")
    parser.add_argument("--publish", nargs="+", metavar="ID", help="Publish one or more resources")
    parser.add_argument("--report", action="store_true", help="Print pilot statistics")
    parser.add_argument("--metrics", action="store_true", help="Print production metrics dashboard")
    parser.add_argument("--export", type=str, metavar="PATH", help="Export pending data as JSON for admin UI")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row

    if args.review:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, title, editor_recommendation, target_audience
            FROM resources
            WHERE editorial_status = 'draft'
            ORDER BY generated_at
        """)
        for r in cur.fetchall():
            print(f"\n── {r['id']} ──")
            print(f"Title: {r['title']}")
            print(f"Rec:   {r['editor_recommendation'][:100]}...")
            print(f"Aud:   {r['target_audience']}")
        return

    if args.publish:
        for rid in args.publish:
            ok, msg = publish_editorial(conn, rid)
            print(f"{'✅' if ok else '❌'} {rid}: {msg}")
        return

    if args.report:
        pilot_report(conn)
        return

    if args.metrics:
        production_metrics(conn)
        return

    if args.export:
        export_review_data(conn, args.export)
        return

    if args.generate:
        resources = get_pilot_resources(conn, limit=args.limit, tier=args.tier, force=args.force)
        print(f"Selected {len(resources)} resources (tier={args.tier or 'all'}, prompt={args.prompt}, limit={args.limit})")
        if args.dry_run:
            for i, r in enumerate(resources[:10]):
                print(f"  {i+1}. [{r['id']}] {r['title'][:60]}")
            if len(resources) > 10:
                print(f"  ... and {len(resources)-10} more")
            return

        ok, fail, skip = 0, 0, 0
        for i, r in enumerate(resources):
            rid = r['id']
            title = r['title'][:50]
            print(f"[{i+1}/{len(resources)}] {rid} {title}")

            # Generate with retry
            data = None
            for attempt in range(3):
                data = generate_editorial(dict(r), prompt_variant=args.prompt)
                if data:
                    break
                print(f"   Retry {attempt+1}/3...")
                time.sleep(2)

            if not data:
                print(f"   ❌ Failed after 3 attempts")
                logging.warning(f"AI_FAIL {rid} {title}")
                fail += 1
                continue

            # Guideline Check
            passed, issues = guideline_check(
                data["editor_recommendation"],
                data["target_audience"],
                data["strengths"],
                data["caveats"],
            )
            if not passed:
                print(f"   ⚠ Guideline issues: {', '.join(issues)}")
                logging.warning(f"GUIDELINE_FAIL {rid}: {'; '.join(issues)}")

            # Write to DB
            wrote, msg = insert_editorial(conn, rid, data, dry_run=args.dry_run)
            if wrote:
                ok += 1
                print(f"   ✅ {msg}")
            else:
                skip += 1
                print(f"   ⏭ {msg}")

        print(f"\nDone: ✅ {ok} generated  ⏭ {skip} skipped  ❌ {fail} failed")
        if fail > 0:
            print(f"Errors logged to: {ERROR_LOG}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()

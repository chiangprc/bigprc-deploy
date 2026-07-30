#!/usr/bin/env python3
"""Phase 10.8.7 — Editorial Content Pilot Generator

Generates Editor's Take content for 50 pilot resources using AI,
with Guideline Check validation before writing to database.

Usage:
  python3 editorial_pilot.py --dry-run       Preview without writing
  python3 editorial_pilot.py --generate      Generate and write (draft)
  python3 editorial_pilot.py --review        List drafts awaiting review
  python3 editorial_pilot.py --publish ID    Publish a reviewed resource
  python3 editorial_pilot.py --report        Print pilot statistics

Rules (from PHASE10_8_1_EDITORIAL_WRITING_GUIDELINE.md):
  - No "非常优秀" "功能强大" "强烈推荐" "值得推荐"
  - No "所有人" in target_audience
  - At least 1 caveat (every resource has limits)
  - At least 1 strength
  - Editor recommendation must be 30+ chars
"""

import os, sys, json, sqlite3, re, time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DB_FILE = os.getenv("DB_FILE", str(SCRIPT_DIR / "database.db"))

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


# ── AI Generation (mock — replace with real API call) ─────────
def generate_editorial(resource):
    """
    Calls AI API to generate Editor's Take content.
    Replace this function body with actual API call.
    Prompt template from PHASE10_8_1_EDITORIAL_WRITING_GUIDELINE.md §7.
    """
    # TODO: Replace with actual API call using the Guideline prompt template
    # For pilot, this would call the same AI endpoint as ai_seo_writer.py
    # but with the editorial-specific system prompt.
    raise NotImplementedError(
        "Replace with actual AI API call. "
        "See PHASE10_8_1_EDITORIAL_WRITING_GUIDELINE.md §7 for prompt template."
    )


# ── Database Operations ──────────────────────────────────────
def get_pilot_resources(conn, limit=50):
    """Select 50 representative resources for the pilot."""
    cur = conn.cursor()
    # Priority: spotlight → CORE collections → SOLID → diverse types
    cur.execute("""
        SELECT r.id, r.title, r.category, r.file_size, r.platform,
               r.version, r.seo_desc,
               GROUP_CONCAT(c.title, ', ') as coll_titles
        FROM resources r
        LEFT JOIN resource_collections rc ON r.id = rc.resource_id
        LEFT JOIN collections c ON rc.collection_id = c.id
        WHERE r.editorial_status IS NULL
        GROUP BY r.id
        ORDER BY
            CASE WHEN rc.spotlight = 1 THEN 0 ELSE 1 END,
            CASE WHEN c.quality = 'CORE' THEN 0
                 WHEN c.quality = 'SOLID' THEN 1
                 ELSE 2 END,
            RANDOM()
        LIMIT ?
    """, (limit,))
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
    parser.add_argument("--review", action="store_true", help="List drafts awaiting review")
    parser.add_argument("--publish", type=str, metavar="ID", help="Publish a resource")
    parser.add_argument("--report", action="store_true", help="Print pilot statistics")
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
        ok, msg = publish_editorial(conn, args.publish)
        print(f"{'✅' if ok else '❌'} {msg}")
        return

    if args.report:
        pilot_report(conn)
        return

    if args.export:
        export_review_data(conn, args.export)
        return

    if args.generate:
        resources = get_pilot_resources(conn)
        print(f"Selected {len(resources)} resources for pilot generation.")
        print("Replace generate_editorial() with real AI API call before running.\n")
        for i, r in enumerate(resources[:5]):
            print(f"  {i+1}. [{r['id']}] {r['title'][:60]}")
        if len(resources) > 5:
            print(f"  ... and {len(resources)-5} more")
        return

    parser.print_help()


if __name__ == "__main__":
    main()

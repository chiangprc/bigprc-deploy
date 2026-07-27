#!/usr/bin/env python3
"""
BigPRC Collection Rule Creation Assistant (Phase 5.3F)

Reads Discovery→Gap output, helps editor propose/apply new collection rules.

Usage:
  python3 collection_rule_assist.py --preview 3    # View group details
  python3 collection_rule_assist.py --propose 3    # Generate draft JSON
  python3 collection_rule_assist.py --apply <slug> # Confirm + write DB
"""

import os, sys, json, sqlite3
from datetime import datetime
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
DB_FILE = os.getenv("DB_FILE") or "/root/scripts/database.db"
REVIEW_DATA = "/var/www/site/web/admin/data/review-data.json"
DRAFTS_DIR = os.path.join(SCRIPT_DIR, "collection_drafts")

# ============================================================
# Helpers
# ============================================================

def load_review_data():
    if not os.path.exists(REVIEW_DATA):
        print(f"❌ Review data not found: {REVIEW_DATA}")
        print("   Run: python3 collection_review_export.py")
        sys.exit(1)
    with open(REVIEW_DATA, "r", encoding="utf-8") as f:
        return json.load(f)


def auto_slug(tags):
    """Generate a simple slug from top 2 tags."""
    return "-".join(t.lower().replace(" ", "-") for t in tags[:2])


def auto_title(tags, category):
    """Generate a title from tags + category."""
    return " ".join(tags[:3])


def auto_rule(tags, primary_cats):
    """Generate rule_suggestion: top 2 tags = AND, rest = OR."""
    tags = list(tags)
    top_cat = list(primary_cats.keys())[0] if primary_cats else None
    return {
        "tags": tags[:2] if len(tags) >= 2 else tags[:1],
        "tags_or": tags[2:] if len(tags) > 2 else [],
        "cats": [top_cat] if top_cat else [],
        "version": 1,
    }


# ============================================================
# --preview
# ============================================================

def cmd_preview(index):
    data = load_review_data()
    groups = data.get("groups", [])
    if index < 0 or index >= len(groups):
        print(f"❌ Group index {index} out of range (0-{len(groups)-1})")
        sys.exit(1)
    g = groups[index]
    cats = g.get("primary_categories", {})
    rule = auto_rule(g["candidate_tags"], cats)

    print()
    print(f"  Group #{index}")
    print(f"  Tags:        {' '.join(g['candidate_tags'])}")
    print(f"  Match:       {g['match_count']} resources")
    if g.get("representative_tags"):
        print(f"  Repr Tags:   {', '.join(g['representative_tags'][:8])}")
    if g.get("title_keywords"):
        print(f"  Keywords:    {', '.join(g['title_keywords'][:8])}")
    print(f"  Samples:     {' | '.join(s['title'][:40] for s in g.get('resource_samples', [])[:3])}")
    print(f"  Categories:  {dict(list(cats.items())[:3])}")
    print(f"  Action:      {g.get('action_label', g.get('action', '?'))}")
    print()
    print(f"  Rule Draft:")
    print(f"    tags:      {json.dumps(rule['tags'], ensure_ascii=False)}")
    print(f"    tags_or:   {json.dumps(rule['tags_or'], ensure_ascii=False)}")
    print(f"    cats:      {json.dumps(rule['cats'], ensure_ascii=False)}")
    print()
    print(f"  To propose:  python3 collection_rule_assist.py --propose {index}")


# ============================================================
# --propose
# ============================================================

def cmd_propose(index, name=None, slug=None):
    data = load_review_data()
    groups = data.get("groups", [])
    if index < 0 or index >= len(groups):
        print(f"❌ Group index {index} out of range (0-{len(groups)-1})")
        sys.exit(1)
    g = groups[index]
    tags = g["candidate_tags"]
    cats = g.get("primary_categories", {})

    cid = slug or auto_slug(tags)
    ctitle = name or auto_title(tags, cats)
    rule = auto_rule(tags, cats)

    draft = {
        "proposed_at": datetime.now().isoformat(),
        "status": "draft",
        "source": {
            "discovery_group_index": index,
            "candidate_tags": tags,
            "generated_from": "collection_discovery",
        },
        "collection": {
            "id": cid,
            "title": ctitle,
            "is_featured": 0,
            "auto_generated": 1,
        },
        "rule_suggestion": rule,
        "preview": {
            "match_count": g["match_count"],
            "samples": [s["title"] for s in g.get("resource_samples", [])[:3]],
            "primary_categories": cats,
        },
    }

    os.makedirs(DRAFTS_DIR, exist_ok=True)
    draft_path = os.path.join(DRAFTS_DIR, f"draft-{cid}.json")
    with open(draft_path, "w", encoding="utf-8") as f:
        json.dump(draft, f, ensure_ascii=False, indent=2)

    print(f"✅ Draft saved: collection_drafts/draft-{cid}.json")
    print()
    print(f"   Review & edit: nano collection_drafts/draft-{cid}.json")
    print(f"   Then:          python3 collection_rule_assist.py --apply {cid}")


# ============================================================
# --apply
# ============================================================

def cmd_apply(slug):
    draft_path = os.path.join(DRAFTS_DIR, f"draft-{slug}.json")
    if not os.path.exists(draft_path):
        print(f"❌ Draft not found: collection_drafts/draft-{slug}.json")
        sys.exit(1)

    with open(draft_path, "r", encoding="utf-8") as f:
        draft = json.load(f)

    cid = draft["collection"]["id"]
    ctitle = draft["collection"]["title"]
    rule_suggestion = draft["rule_suggestion"]
    expected_match = draft["preview"]["match_count"]

    # Safety check 1: collection already exists
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    exists = cursor.execute("SELECT 1 FROM collections WHERE id=?", (cid,)).fetchone()
    if exists:
        print(f"❌ Collection '{cid}' already exists in database")
        conn.close()
        sys.exit(1)

    # Safety check 2: Rule Engine match
    from rule_engine import match_collection
    result = match_collection(cursor, rule_suggestion, collection_id=cid)
    actual_match = result.count
    if actual_match == 0 or actual_match != expected_match:
        print(f"⚠️  Match count changed")
        print(f"   Draft:   {expected_match}")
        print(f"   Current: {actual_match}")
        print(f"   Cannot proceed — review rule_suggestion in draft JSON")
        conn.close()
        sys.exit(1)

    # Confirmation
    print()
    print(f"  ⚠️  Will write to database")
    print()
    print(f"  Collection:  {cid}")
    print(f"  Title:       {ctitle}")
    print(f"  Match:       {actual_match} resources")
    print()
    print(f"  Tables affected:")
    print(f"    collections           INSERT 1 row")
    print(f"    resource_collections  INSERT {actual_match} rows")
    print()
    ans = input("  Type YES to confirm: ").strip()
    if ans != "YES":
        print("  Cancelled.")
        conn.close()
        sys.exit(0)

    # Write (single transaction: atomic)
    try:
        rule_json = json.dumps(rule_suggestion, ensure_ascii=False)
        cursor.execute(
            "INSERT INTO collections (id, title, rule_json, status, auto_generated, is_featured) "
            "VALUES (?,?,?,'published',1,0)",
            (cid, ctitle, rule_json))

        inserted = 0
        for rid in result.resource_ids:
            cursor.execute(
                "INSERT OR IGNORE INTO resource_collections (resource_id, collection_id, score, source) "
                "VALUES (?,?,1.0,'auto')",
                (rid, cid))
            inserted += cursor.rowcount

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Transaction failed, rolled back: {e}")
        conn.close()
        sys.exit(1)

    # Update draft status
    draft["status"] = "applied"
    with open(draft_path, "w", encoding="utf-8") as f:
        json.dump(draft, f, ensure_ascii=False, indent=2)

    conn.close()
    print(f"✅ Created collection {cid} — {inserted} resources linked")


# ============================================================
# CLI
# ============================================================

def main():
    args = sys.argv[1:]
    if not args:
        print("Usage:")
        print("  python3 collection_rule_assist.py --preview <index>")
        print("  python3 collection_rule_assist.py --propose <index> [--name X] [--slug Y]")
        print("  python3 collection_rule_assist.py --apply <slug>")
        sys.exit(1)

    if args[0] == "--preview":
        cmd_preview(int(args[1]))
    elif args[0] == "--propose":
        idx = int(args[1])
        name = slug = None
        for i, a in enumerate(args):
            if a == "--name" and i+1 < len(args): name = args[i+1]
            if a == "--slug" and i+1 < len(args): slug = args[i+1]
        cmd_propose(idx, name, slug)
    elif args[0] == "--apply":
        cmd_apply(args[1])
    else:
        print(f"Unknown command: {args[0]}")


if __name__ == "__main__":
    main()

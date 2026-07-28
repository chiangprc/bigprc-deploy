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
def find_group(group_id):
    """By group_id find the group in review-data.json, return (index, group_dict)."""
    data = load_review_data()
    groups = data.get("groups", [])
    for i, g in enumerate(groups):
        if g.get("group_id") == group_id:
            return i, g
    print(f"❌ Group '{group_id}' not found in review-data.json")
    print("   Run: python3 collection_review_export.py")
    sys.exit(1)


# ============================================================
# --preview
# ============================================================

def cmd_preview(group_id):
    idx, g = find_group(group_id)
    cats = g.get("primary_categories", {})
    rule = auto_rule(g["candidate_tags"], cats)

    print()
    print(f"  Group: {group_id}")
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
    print(f"  To propose:  python3 collection_rule_assist.py --propose {group_id}")


# ============================================================
# --propose
# ============================================================

def cmd_propose(group_id, name=None, slug=None):
    idx, g = find_group(group_id)
    tags = g["candidate_tags"]
    cats = g.get("primary_categories", {})

    cid = slug or auto_slug(tags)
    ctitle = name or auto_title(tags, cats)
    rule = auto_rule(tags, cats)

    draft = {
        "proposed_at": datetime.now().isoformat(),
        "status": "draft",
        "source": {
            "group_id": group_id,
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

# ============================================================
# --simulate
# ============================================================

def cmd_simulate(collection_id, extra_args):
    """Simulate rule changes without writing to DB."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT id, title, rule_json FROM collections WHERE id=? AND status='published'",
        (collection_id,)).fetchone()
    if not row:
        print(f"❌ Collection '{collection_id}' not found")
        conn.close()
        sys.exit(1)

    cid, ctitle, rule_raw = row
    try:
        current_rule = json.loads(rule_raw) if rule_raw else {}
    except (json.JSONDecodeError, TypeError):
        print(f"❌ Invalid rule_json for {cid}")
        conn.close()
        sys.exit(1)

    # Build simulated rule
    simulated_rule = json.loads(json.dumps(current_rule))  # deep copy

    # Parse modifications
    add_tags = []
    add_tags_or = []
    custom_rule = None
    i = 0
    while i < len(extra_args):
        if extra_args[i] == "--add-tags" and i+1 < len(extra_args):
            add_tags.append(extra_args[i+1]); i += 2; continue
        if extra_args[i] == "--add-tags-or" and i+1 < len(extra_args):
            add_tags_or.append(extra_args[i+1]); i += 2; continue
        if extra_args[i] == "--rule" and i+1 < len(extra_args):
            try:
                custom_rule = json.loads(extra_args[i+1])
            except (json.JSONDecodeError, TypeError):
                print(f"❌ Invalid JSON for --rule parameter")
                conn.close()
                sys.exit(1)
            i += 2; continue
        i += 1

    if custom_rule:
        simulated_rule = custom_rule
    else:
        if add_tags:
            simulated_rule["tags"] = list(set(simulated_rule.get("tags", []) + add_tags))
        if add_tags_or:
            simulated_rule["tags_or"] = list(set(simulated_rule.get("tags_or", []) + add_tags_or))

    # Match both
    from rule_engine import match_collection
    current_match = match_collection(cursor, current_rule, collection_id=cid)
    simulated_match = match_collection(cursor, simulated_rule, collection_id=cid)

    current_ids = set(current_match.resource_ids)
    simulated_ids = set(simulated_match.resource_ids)
    added_ids = simulated_ids - current_ids
    removed_ids = current_ids - simulated_ids

    # Samples
    def sample_titles(ids, limit=20):
        result = []
        for rid in sorted(ids)[:limit]:
            t = cursor.execute("SELECT title FROM resources WHERE res_id=?", (rid,)).fetchone()
            result.append(f"{rid}  {t[0][:60]}" if t else rid)
        return result

    conn.close()

    print()
    print(f"── Rule Simulation: {cid} ──")
    print()
    print(f"  当前规则                模拟规则")
    print(f"  {json.dumps(current_rule, ensure_ascii=False):40s}  {json.dumps(simulated_rule, ensure_ascii=False)}")
    print()
    print(f"  匹配数: {current_match.count:<20d} 匹配数: {simulated_match.count}  ({'+' if simulated_match.count >= current_match.count else ''}{simulated_match.count - current_match.count})")
    print(f"  {'─'*50}")
    if added_ids:
        print(f"\n  新增资源 ({len(added_ids)}):")
        for s in sample_titles(added_ids):
            print(f"    {s}")
    if removed_ids:
        print(f"\n  移除资源 ({len(removed_ids)}):")
        for s in sample_titles(removed_ids):
            print(f"    {s}")
    if not added_ids and not removed_ids:
        print(f"\n  ✅ 规则变化不影响匹配结果")
    print()
    print(f"  💡 To apply: python3 collection_rule_assist.py --propose {cid}")
    print(f"     edit collection_drafts/draft-{cid}.json")
    print(f"     python3 collection_rule_assist.py --apply {cid}")
    print()


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage:")
        print("  python3 collection_rule_assist.py --preview <group_id>")
        print("  python3 collection_rule_assist.py --propose <group_id> [--name X] [--slug Y]")
        print("  python3 collection_rule_assist.py --apply <slug>")
        print("  python3 collection_rule_assist.py --simulate <collection_id> [--add-tags X] [--add-tags-or Y] [--rule '...']")
        sys.exit(1)

    if args[0] == "--preview":
        cmd_preview(args[1])
    elif args[0] == "--simulate":
        cmd_simulate(args[1], args[2:])
    elif args[0] == "--propose":
        gid = args[1]
        name = slug = None
        for i, a in enumerate(args):
            if a == "--name" and i+1 < len(args): name = args[i+1]
            if a == "--slug" and i+1 < len(args): slug = args[i+1]
        cmd_propose(gid, name, slug)
    elif args[0] == "--apply":
        cmd_apply(args[1])
    else:
        print(f"Unknown command: {args[0]}")


if __name__ == "__main__":
    main()

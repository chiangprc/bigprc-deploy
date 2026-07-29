#!/usr/bin/env python3
"""
BigPRC Collection Curate CLI — Resource Spotlight (Phase 10.2)

Editor-curated featured resources within collections.
Not algorithmic scoring. Human editorial judgment.

Commands:
  python3 collection_curate.py --spotlight bbc-nature p001
  python3 collection_curate.py --unspotlight bbc-nature p001
  python3 collection_curate.py --list bbc-nature
  python3 collection_curate.py --list-all

Config: /root/scripts/.env
"""

import os, sys, sqlite3
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
DB_FILE = os.getenv("DB_FILE") or "/root/scripts/database.db"


def cmd_spotlight(cursor, cid, rid):
    title = cursor.execute("SELECT title FROM resources WHERE res_id=?", (rid,)).fetchone()
    cname = cursor.execute("SELECT title FROM collections WHERE id=?", (cid,)).fetchone()
    if not title:
        print(f"❌ Resource '{rid}' not found"); return
    if not cname:
        print(f"❌ Collection '{cid}' not found"); return

    rel = cursor.execute("SELECT 1 FROM resource_collections WHERE resource_id=? AND collection_id=?",
                         (rid, cid)).fetchone()
    if not rel:
        print(f"❌ Resource '{rid}' is not in collection '{cid}'"); return

    cursor.execute("UPDATE resource_collections SET spotlight=1 WHERE resource_id=? AND collection_id=?",
                   (rid, cid))
    cursor.connection.commit()
    print(f"✅ {title[0][:50]} → spotlight in {cname[0]}")


def cmd_unspotlight(cursor, cid, rid):
    cursor.execute("UPDATE resource_collections SET spotlight=0 WHERE resource_id=? AND collection_id=?",
                   (rid, cid))
    cursor.connection.commit()
    title = cursor.execute("SELECT title FROM resources WHERE res_id=?", (rid,)).fetchone()
    cname = cursor.execute("SELECT title FROM collections WHERE id=?", (cid,)).fetchone()
    print(f"✅ {(title[0][:50] if title else rid)} — removed spotlight from {(cname[0] if cname else cid)}")


def cmd_list(cursor, cid):
    cname = cursor.execute("SELECT title FROM collections WHERE id=?", (cid,)).fetchone()
    if not cname:
        print(f"❌ Collection '{cid}' not found"); return
    rows = cursor.execute("""
        SELECT r.res_id, r.title FROM resources r
        JOIN resource_collections rc ON r.res_id = rc.resource_id
        WHERE rc.collection_id=? AND rc.spotlight=1
        ORDER BY rc.score DESC
    """, (cid,)).fetchall()
    if not rows:
        print(f"  No spotlight resources in {cname[0]}")
        return
    print(f"  Spotlight: {cname[0]} ({len(rows)} resources)")
    for rid, rtitle in rows:
        print(f"  [*] {rid}  {rtitle}")


def cmd_list_all(cursor):
    rows = cursor.execute("""
        SELECT c.id, c.title, COUNT(rc.resource_id) as cnt
        FROM collections c
        JOIN resource_collections rc ON c.id = rc.collection_id
        WHERE rc.spotlight = 1
        GROUP BY c.id ORDER BY cnt DESC
    """).fetchall()
    if not rows:
        print("  No spotlight resources in any collection.")
        return
    for cid, ctitle, cnt in rows:
        print(f"  {cid:25s}  {ctitle:30s}  {cnt} spotlighted")


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage:")
        print("  python3 collection_curate.py --spotlight <collection_id> <resource_id>")
        print("  python3 collection_curate.py --unspotlight <collection_id> <resource_id>")
        print("  python3 collection_curate.py --list <collection_id>")
        print("  python3 collection_curate.py --list-all")
        sys.exit(1)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if args[0] == '--spotlight':
        cmd_spotlight(cursor, args[1], args[2])
    elif args[0] == '--unspotlight':
        cmd_unspotlight(cursor, args[1], args[2])
    elif args[0] == '--list':
        cmd_list(cursor, args[1])
    elif args[0] == '--list-all':
        cmd_list_all(cursor)
    else:
        print(f"Unknown command: {args[0]}")

    conn.close()


if __name__ == "__main__":
    main()

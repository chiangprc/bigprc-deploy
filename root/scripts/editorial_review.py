#!/usr/bin/env python3
"""
BigPRC Editorial Review CLI — Editorial Workflow status transitions (Phase 9.4B)

Commands:
  python3 editorial_review.py --status              # All collections
  python3 editorial_review.py --status bbc-nature   # Single collection
  python3 editorial_review.py --review bbc-nature   # draft → reviewed
  python3 editorial_review.py --approve bbc-nature  # reviewed → approved
  python3 editorial_review.py --reject bbc-nature   # any → rejected
  python3 editorial_review.py --rollback bbc-nature # restore previous status
  python3 editorial_review.py --history bbc-nature  # show audit log
  python3 editorial_review.py --dry-run --review bbc-nature  # preview only

Config: /root/scripts/.env
"""

import os, sys, json, sqlite3
from datetime import datetime
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
DB_FILE = os.getenv("DB_FILE") or "/root/scripts/database.db"

VALID_STATUSES = {'draft', 'reviewed', 'approved', 'rejected'}

# State transition rules: {current: {action: next_status}}
TRANSITIONS = {
    'draft':    {'review': 'reviewed',  'reject': 'rejected'},
    'reviewed': {'approve': 'approved', 'reject': 'rejected'},
    'approved': {'reject': 'rejected'},
    'rejected': {'review': 'reviewed'},
}


def get_status(cursor, cid):
    row = cursor.execute(
        "SELECT editorial_status FROM collection_content WHERE collection_id=?",
        (cid,)).fetchone()
    return (row[0] if row else 'draft') if row else 'draft'


def check_transition(current, action):
    if current not in TRANSITIONS:
        return f"Unknown current status: {current}"
    allowed = TRANSITIONS[current]
    if action not in allowed:
        return f"Cannot {action} from {current}. Allowed: {', '.join(allowed.keys())}"
    return None  # OK


def log_audit(cursor, cid, action, old_st, new_st, metadata=None):
    cursor.execute("""
        INSERT INTO collection_audit_log
        (collection_id, action, old_status, new_status, operator, metadata, created_at)
        VALUES (?, ?, ?, ?, 'editor', ?, ?)
    """, (cid, action, old_st, new_st, json.dumps(metadata or {}),
          datetime.now().isoformat()))


def cmd_status(cursor, target=None):
    where = "WHERE c.id = ?" if target else ""
    params = (target,) if target else ()
    rows = cursor.execute(f"""
        SELECT c.id, c.title, COALESCE(cc.editorial_status,'draft'),
               COALESCE(cc.editor_note,'')!='' as has_en
        FROM collections c
        LEFT JOIN collection_content cc ON c.id = cc.collection_id
        {where} ORDER BY c.title
    """, params).fetchall()
    if not rows:
        print("No collections found.")
        return
    for cid, title, st, has_en in rows:
        icon = {'draft':'🟡','reviewed':'🔵','approved':'🟢','rejected':'🔴'}.get(st,'?')
        print(f"  {icon} {st:10s}  {cid:25s}  {title}")


def cmd_transition(cursor, cid, action, dry_run):
    title_row = cursor.execute("SELECT title FROM collections WHERE id=?", (cid,)).fetchone()
    if not title_row:
        print(f"❌ Collection '{cid}' not found")
        return
    title = title_row[0]
    current = get_status(cursor, cid)
    if action == 'rollback':
        return cmd_rollback(cursor, cid, current, dry_run)

    err = check_transition(current, action)
    if err:
        print(f"  ❌ {title}: {err}")
        return
    new_status = TRANSITIONS[current][action]

    ts_field = {'review': 'reviewed_at', 'approve': 'approved_at'}.get(action)

    if dry_run:
        print(f"  🧪 DRY RUN: {title}: {current} → {new_status}")
        return

    try:
        if ts_field:
            cursor.execute(f"UPDATE collection_content SET editorial_status=?, {ts_field}=? WHERE collection_id=?",
                           (new_status, datetime.now().isoformat(), cid))
        else:
            cursor.execute("UPDATE collection_content SET editorial_status=? WHERE collection_id=?",
                           (new_status, cid))
        log_audit(cursor, cid, action, current, new_status)
        cursor.connection.commit()
        print(f"  ✅ {title}: {current} → {new_status}")
    except Exception as e:
        cursor.connection.rollback()
        print(f"  ❌ {title}: {e}")


def cmd_rollback(cursor, cid, current, dry_run):
    prev = cursor.execute("""
        SELECT old_status FROM collection_audit_log
        WHERE collection_id=? AND action!='rollback'
        ORDER BY id DESC LIMIT 1
    """, (cid,)).fetchone()
    if not prev:
        print(f"  ❌ No previous status in audit log for {cid}")
        return
    prev_st = prev[0]
    title = cursor.execute("SELECT title FROM collections WHERE id=?", (cid,)).fetchone()[0]

    if dry_run:
        print(f"  🧪 DRY RUN: {title}: {current} → {prev_st} (rollback)")
        return

    try:
        cursor.execute("UPDATE collection_content SET editorial_status=? WHERE collection_id=?",
                       (prev_st, cid))
        log_audit(cursor, cid, 'rollback', current, prev_st)
        cursor.connection.commit()
        print(f"  ✅ {title}: {current} → {prev_st} (rollback)")
    except Exception as e:
        cursor.connection.rollback()
        print(f"  ❌ {e}")


def cmd_history(cursor, cid):
    rows = cursor.execute("""
        SELECT action, old_status, new_status, operator, created_at
        FROM collection_audit_log WHERE collection_id=?
        ORDER BY id DESC LIMIT 20
    """, (cid,)).fetchall()
    if not rows:
        print(f"  No audit history for {cid}")
        return
    for action, old_st, new_st, op, ts in rows:
        print(f"  {ts[:19]}  {action:10s}  {old_st or '?':10s} → {new_st or '?':10s}")


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python3 editorial_review.py --status [id]")
        print("       python3 editorial_review.py --review <id>")
        print("       python3 editorial_review.py --approve <id>")
        print("       python3 editorial_review.py --reject <id>")
        print("       python3 editorial_review.py --rollback <id>")
        print("       python3 editorial_review.py --history <id>")
        print("       python3 editorial_review.py --dry-run --review <id>")
        sys.exit(1)

    dry_run = '--dry-run' in args
    action_args = [a for a in args if a != '--dry-run']

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    if action_args[0] == '--status':
        cmd_status(cursor, action_args[1] if len(action_args) > 1 else None)
    elif action_args[0] == '--history':
        cmd_history(cursor, action_args[1])
    elif action_args[0] in ('--review', '--approve', '--reject', '--rollback'):
        action = action_args[0].lstrip('--')
        cmd_transition(cursor, action_args[1], action, dry_run)
    else:
        print(f"Unknown command: {action_args[0]}")

    conn.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""BigPRC shared database path resolution.

Every script that needs the production database MUST use this helper.
Never derive DB location from SCRIPT_DIR or __file__.

Usage:
    from db_helper import get_db
    conn = sqlite3.connect(get_db())
"""

import os

_PRODUCTION_DB = "/root/scripts/database.db"


def get_db():
    """Return the production database path.

    Resolution order:
    1. DB_FILE environment variable (from /root/scripts/.env)
    2. Default: /root/scripts/database.db (production)

    Never returns a path derived from the script's own location.
    """
    return os.getenv("DB_FILE", _PRODUCTION_DB)

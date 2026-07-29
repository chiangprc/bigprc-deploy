#!/usr/bin/env bash
# ============================================================
# sync_tokens.sh — Design Token sync
# Copies the canonical _tokens.css to all consumer locations.
# ⚠  _tokens.css is the SINGLE SOURCE OF TRUTH.
# ⚠  Do NOT edit copies manually — edit _tokens.css, then
#    run this script.
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/root/scripts/templates/_tokens.css"

if [ ! -f "$SRC" ]; then
    echo "ERROR: canonical source not found: $SRC"
    exit 1
fi

# custom-pages/css/design-tokens.css (for standalone pages via <link>)
DST_CSS="$SCRIPT_DIR/root/custom-pages/css/design-tokens.css"
mkdir -p "$(dirname "$DST_CSS")"
cp "$SRC" "$DST_CSS"
echo "✅  $DST_CSS"

echo ""
echo "Design tokens synced from canonical source."
echo "  source: $SRC"

#!/usr/bin/env bash
# ==========================================
# BigPRC Local Preview (macOS / Linux)
# Usage: bash preview.sh [port]
# ==========================================
set -e

PORT=${1:-8765}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/venv/bin/python3"
SERVER_SCRIPT="$SCRIPT_DIR/local_server.py"
SITE_DIR="$SCRIPT_DIR/var/www/site/web"

# ---- 1. locate Python (prefer SSD-local venv) ----
if [ -x "$VENV_PYTHON" ]; then
    PYTHON="$VENV_PYTHON"
    echo -e "\033[90m[OK] Using SSD-local venv Python\033[0m"
else
    PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || echo "")
    if [ -z "$PYTHON" ]; then
        echo -e "\033[31mERROR: Python not found on this machine.\033[0m"
        echo -e "\033[33m       Install Python 3.9+ from https://python.org\033[0m"
        echo -e "\033[33m       Then run: bash setup.sh\033[0m"
        exit 1
    fi
    echo -e "\033[33m[WARN] venv not found, using system Python\033[0m"
    echo -e "\033[33m       Run: bash setup.sh\033[0m"
fi

# ---- 2. dependency self-check ----
echo -ne "\033[90mChecking dependencies ... \033[0m"
CHECK=$("$PYTHON" -c "import jinja2, dotenv, requests, http.server, urllib.parse, mimetypes; print('OK')" 2>&1) || true
if [ "$CHECK" != "OK" ]; then
    echo ""
    echo -e "\033[31mERROR: Missing Python packages.\033[0m"
    echo -e "\033[33m       Run: bash setup.sh\033[0m"
    exit 1
fi
echo -e "\033[90mOK\033[0m"

# ---- 3. locate server script ----
if [ ! -f "$SERVER_SCRIPT" ]; then
    echo -e "\033[31mERROR: local_server.py not found at $SERVER_SCRIPT\033[0m"
    exit 1
fi

# ---- 4. locate generated site ----
if [ ! -f "$SITE_DIR/index.html" ]; then
    echo -e "\033[31mERROR: Generated site missing. Run: python root/scripts/auto_generate.py\033[0m"
    exit 1
fi
FILE_COUNT=$(find "$SITE_DIR" -type f | wc -l | tr -d ' ')
echo -e "\033[90m[OK] Generated site found (${FILE_COUNT} files)\033[0m"

# ---- 5. start server ----
URL="http://127.0.0.1:$PORT"

echo ""
echo "=========================================="
echo " BigPRC Local Preview (127.0.0.1 only)"
echo " Python : $PYTHON"
echo " URL    : $URL"
echo " Stop   : Ctrl+C"
echo "=========================================="

# Open browser
if command -v open &>/dev/null; then
    open "$URL"
elif command -v xdg-open &>/dev/null; then
    xdg-open "$URL"
fi

cd "$SCRIPT_DIR"
"$PYTHON" "$SERVER_SCRIPT" "$PORT"

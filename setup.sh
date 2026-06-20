#!/usr/bin/env bash
# ==========================================
# BigPRC One-Time Setup — create local venv on SSD
# Run ONCE per new Mac:  bash setup.sh
# Auto-installs Python if missing (Homebrew / direct download).
# ==========================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python3"

# --------------------------------------------------
# Helper: find a working python3 in PATH
# --------------------------------------------------
find_python() {
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            echo "$(command -v "$cmd")"
            return 0
        fi
    done
    # Scan common macOS locations
    for dir in /usr/local/bin /opt/homebrew/bin /Library/Frameworks/Python.framework/Versions/3.*/bin; do
        for exe in "$dir"/python3 "$dir"/python; do
            if [ -x "$exe" ]; then
                echo "$exe"
                return 0
            fi
        done
    done
    return 1
}

# --------------------------------------------------
# Auto-install Python if missing
# --------------------------------------------------
install_python_auto() {
    echo ""
    echo -e "\033[33mPython not found. Attempting automatic installation ...\033[0m"

    # Strategy A: Homebrew (preferred on macOS)
    if command -v brew &>/dev/null; then
        echo -e "\033[90m[A] Homebrew found, installing python@3.12 ...\033[0m"
        brew install python@3.12 2>&1 | tail -5
        if command -v python3.12 &>/dev/null; then
            echo -e "\033[32m[OK] Python 3.12 installed via Homebrew: $(command -v python3.12)\033[0m"
            echo "$(command -v python3.12)"
            return 0
        fi
        # brew symlinks may not be in PATH yet
        if [ -x "/opt/homebrew/bin/python3.12" ]; then
            export PATH="/opt/homebrew/bin:$PATH"
            echo "/opt/homebrew/bin/python3.12"
            return 0
        fi
        if [ -x "/usr/local/bin/python3.12" ]; then
            export PATH="/usr/local/bin:$PATH"
            echo "/usr/local/bin/python3.12"
            return 0
        fi
        echo -e "\033[33m[WARN] Homebrew install seemed to succeed but python3.12 not found\033[0m"
    else
        echo -e "\033[90m[A] Homebrew not installed\033[0m"
        echo -e "\033[90m    To install Homebrew: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"\033[0m"
    fi

    # Strategy B: direct download from python.org (macOS universal2)
    echo -e "\033[90m[B] Downloading Python 3.12.9 for macOS ...\033[0m"
    local PKG_URL="https://www.python.org/ftp/python/3.12.9/python-3.12.9-macos11.pkg"
    local PKG_FILE="/tmp/python-3.12.9-macos11.pkg"

    curl -fSL --connect-timeout 30 --max-time 300 -o "$PKG_FILE" "$PKG_URL" 2>&1 || {
        echo -e "\033[31m[ERROR] Download failed. Install Python manually from https://python.org\033[0m"
        rm -f "$PKG_FILE"
        return 1
    }

    echo -e "\033[90m[B] Downloaded. Installing (may ask for password) ...\033[0m"
    sudo installer -pkg "$PKG_FILE" -target / 2>&1
    rm -f "$PKG_FILE"

    # Find the newly installed Python
    for dir in /Library/Frameworks/Python.framework/Versions/3.12/bin /Applications/Python\ 3.12; do
        if [ -x "$dir/python3" ]; then
            echo -e "\033[32m[OK] Python installed: $dir/python3\033[0m"
            echo "$dir/python3"
            return 0
        fi
    done

    echo ""
    echo -e "\033[31mAutomatic installation failed.\033[0m"
    echo -e "\033[33mInstall Python 3.9+ from https://python.org, then re-run: bash setup.sh\033[0m"
    return 1
}

# ============================================================
# Step 1: check system Python (auto-install if missing)
# ============================================================
PYTHON_SYSTEM=$(find_python)
if [ -z "$PYTHON_SYSTEM" ]; then
    PYTHON_SYSTEM=$(install_python_auto)
    if [ -z "$PYTHON_SYSTEM" ]; then exit 1; fi
fi
echo -e "\033[32m[OK] System Python: $PYTHON_SYSTEM\033[0m"
$PYTHON_SYSTEM --version

# ============================================================
# Step 2: create venv on SSD
# ============================================================
if [ -x "$PYTHON_BIN" ]; then
    echo -e "\033[90m[SKIP] venv already exists at $VENV_DIR\033[0m"
else
    echo "Creating venv at $VENV_DIR ..."
    $PYTHON_SYSTEM -m venv "$VENV_DIR"
    if [ ! -x "$PYTHON_BIN" ]; then
        echo -e "\033[31mERROR: venv creation failed\033[0m"
        exit 1
    fi
    echo -e "\033[32m[OK] venv created\033[0m"
fi

# ============================================================
# Step 3: install packages into venv
# ============================================================
echo "Installing packages into venv ..."
"$PYTHON_BIN" -m pip install --quiet jinja2 python-dotenv requests
echo -e "\033[32m[OK] Packages: jinja2, python-dotenv, requests\033[0m"

# ============================================================
# Step 4: verify
# ============================================================
echo "Verifying ..."
"$PYTHON_BIN" -c "import jinja2, dotenv, requests; print('All imports OK')"

echo ""
echo "=========================================="
echo " Setup complete. Start preview with:"
echo "   bash preview.sh"
echo "=========================================="

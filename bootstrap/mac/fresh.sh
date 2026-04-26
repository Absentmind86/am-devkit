#!/usr/bin/env bash
# AM-DevKit macOS bootstrapper
# Usage: bash fresh.sh [gui|scan|cli] [extra installer args...]
#
# One-liner (after cloning):
#   bash bootstrap/mac/fresh.sh
#
# Or set env vars to control clone target:
#   INSTALL_PATH=~/dev/am-devkit BRANCH=main bash bootstrap/mac/fresh.sh
set -euo pipefail

REPO="https://github.com/Absentmind86/am-devkit.git"
INSTALL_PATH="${INSTALL_PATH:-$HOME/am-devkit}"
BRANCH="${BRANCH:-main}"
MODE="${1:-gui}"

# --- Ensure Homebrew ---
if ! command -v brew &>/dev/null; then
    echo "[am-devkit] Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add brew to PATH for Apple Silicon
    if [ -f "/opt/homebrew/bin/brew" ]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
fi

# --- Ensure git (Xcode CLT or brew) ---
if ! command -v git &>/dev/null; then
    echo "[am-devkit] Installing git via brew..."
    brew install git
fi

# --- Clone or update repo ---
if [ ! -d "$INSTALL_PATH/.git" ]; then
    echo "[am-devkit] Cloning into $INSTALL_PATH..."
    git clone --branch "$BRANCH" "$REPO" "$INSTALL_PATH"
else
    echo "[am-devkit] Repo exists at $INSTALL_PATH — pulling latest..."
    git -C "$INSTALL_PATH" pull --ff-only
fi

cd "$INSTALL_PATH"

# --- Ensure Python 3.11+ ---
if ! command -v python3 &>/dev/null || ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    echo "[am-devkit] Installing Python 3.12 via brew..."
    brew install python@3.12
    # Ensure the brew python is on PATH
    export PATH="$(brew --prefix python@3.12)/bin:$PATH"
fi

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    echo "[am-devkit] ERROR: Python 3.11+ required. Please upgrade and re-run."
    exit 1
fi

# --- Install pip deps ---
echo "[am-devkit] Installing Python dependencies..."
python3 -m pip install -r requirements.txt --quiet

# --- Launch ---
case "$MODE" in
    gui)
        echo "[am-devkit] Launching GUI..."
        python3 -m core.gui
        ;;
    scan)
        echo "[am-devkit] Running system scan..."
        python3 core/system_scan.py
        ;;
    *)
        echo "[am-devkit] Launching installer..."
        shift || true
        python3 -m core.installer "$@"
        ;;
esac

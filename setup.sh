#!/usr/bin/env bash
set -euo pipefail

echo "=== Crossword Helper Setup ==="
echo ""

# novice-readiness spec 0.2.4 §5 (SETUP-MISSING): a failed prerequisite check prints
# one "Missing: <tool> <minimum version> — install from <url>" line and exits 1
# before anything is created. Checks run in order: python3, node, npm.
PYTHON_MISSING="Missing: python3 3.9 or later — install from https://python.org/downloads"
NODE_MISSING="Missing: node 18 or later — install from https://nodejs.org"
NPM_MISSING="Missing: npm (installed with Node.js 18 or later) — install from https://nodejs.org"

# --- Check Python version ---
if ! command -v python3 &>/dev/null; then
    echo "$PYTHON_MISSING"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]; }; then
    echo "$PYTHON_MISSING"
    exit 1
fi
echo "[ok] Python $PYTHON_VERSION"

# --- Check Node.js version ---
if ! command -v node &>/dev/null; then
    echo "$NODE_MISSING"
    exit 1
fi

NODE_MAJOR=$(node -e 'console.log(process.versions.node.split(".")[0])')
if [ "$NODE_MAJOR" -lt 18 ]; then
    echo "$NODE_MISSING"
    exit 1
fi
echo "[ok] Node.js $(node --version)"

# --- Check npm ---
if ! command -v npm &>/dev/null; then
    echo "$NPM_MISSING"
    exit 1
fi

# --- Create virtual environment ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

# novice-readiness spec 0.2.4 §5 (venv): Debian/Ubuntu without python3-venv leave a
# partial venv/ with no bin/pip. A venv/ is trusted only if bin/pip exists: on either
# branch a pip-less venv/ is removed, so the next run starts clean, and the message
# names the package.
VENV_MISSING="Install python3-venv (for example: sudo apt install python3-venv), then run ./setup.sh again"

require_venv_pip() {
    if [ ! -x "$VENV_DIR/bin/pip" ]; then
        rm -rf "$VENV_DIR"
        echo "$VENV_MISSING"
        exit 1
    fi
}

if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "Creating Python virtual environment..."
    # `|| true`: a failing `-m venv` must reach the pip check (set -e would abort first)
    python3 -m venv "$VENV_DIR" || true
    require_venv_pip
    echo "[ok] Virtual environment created at venv/"
else
    require_venv_pip
    echo "[ok] Virtual environment already exists"
fi

# --- Activate venv and install pip dependencies ---
echo ""
echo "Installing Python dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" --quiet
echo "[ok] Python dependencies installed"

# --- Install npm dependencies ---
echo ""
echo "Installing Node.js dependencies..."
cd "$SCRIPT_DIR"
# novice-readiness spec 0.2.4 §5 (#49): ci installs from the lock file and never rewrites it
# 0.2.6 §5: a failing ci shows npm's own output and stops. No --silent: real npm prints nothing
# on failure under it; capturing into npm_out already keeps success quiet.
if ! npm_out=$(npm ci 2>&1); then
    echo "$npm_out"
    echo "Error: npm ci failed (output above). Check that package-lock.json matches package.json and your network works, then run ./setup.sh again"
    exit 1
fi
echo "[ok] Node.js dependencies installed"

# --- Build frontend ---
echo ""
echo "Building frontend..."
npm run build --silent
echo "[ok] Frontend built to frontend/dist/"

# --- Done ---
echo ""
echo "=== Setup complete ==="
echo ""
echo "To run the app:"
echo "  source venv/bin/activate"
echo "  python3 run.py"
echo ""
echo "Then open http://localhost:5000 in your browser."
echo ""
echo "For development mode (hot reload):"
echo "  Terminal 1: source venv/bin/activate && python3 run.py"
echo "  Terminal 2: npm run dev"
echo "  Then open http://localhost:3000"

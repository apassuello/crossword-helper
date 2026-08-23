#!/usr/bin/env bash
set -euo pipefail

echo "=== Crossword Helper Setup ==="
echo ""

# --- Check Python version ---
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 not found. Install Python 3.9 or later."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]; }; then
    echo "Error: Python 3.9+ required (found $PYTHON_VERSION)."
    exit 1
fi
echo "[ok] Python $PYTHON_VERSION"

# --- Check Node.js version ---
if ! command -v node &>/dev/null; then
    echo "Error: node not found. Install Node.js 18 or later."
    exit 1
fi

NODE_MAJOR=$(node -e 'console.log(process.versions.node.split(".")[0])')
if [ "$NODE_MAJOR" -lt 18 ]; then
    echo "Error: Node.js 18+ required (found $(node --version))."
    exit 1
fi
echo "[ok] Node.js $(node --version)"

# --- Create virtual environment ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "[ok] Virtual environment created at venv/"
else
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
npm install --silent 2>&1 | tail -1
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

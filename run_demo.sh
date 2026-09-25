#!/usr/bin/env bash
# NETRA-DR — Phase 1 Prototype Demo Launcher (Linux/macOS/Git Bash on Windows)
# Usage: bash run_demo.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "============================================================"
echo "  NETRA-DR Phase 1 Prototype Demo Launcher"
echo "============================================================"
echo ""

PYTHON_EXEC="python"
if [ -f "external/EyeQ/.venv/bin/python" ]; then
    PYTHON_EXEC="external/EyeQ/.venv/bin/python"
    echo "[*] Using EyeQ Python environment: $PYTHON_EXEC"
elif [ -f "external/EyeQ/.venv/Scripts/python.exe" ]; then
    PYTHON_EXEC="external/EyeQ/.venv/Scripts/python.exe"
    echo "[*] Using EyeQ Python environment: $PYTHON_EXEC"
fi

echo "[1/2] Verifying Python dependencies..."
"$PYTHON_EXEC" -m pip install -r requirements.txt --quiet || true

echo ""
echo "[2/2] Starting NETRA-DR demo server..."
echo "      Open your browser at: http://127.0.0.1:5000"
echo "      Press Ctrl+C to stop."
echo ""

"$PYTHON_EXEC" app/app.py

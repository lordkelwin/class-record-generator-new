#!/usr/bin/env bash
set -e

# Change directory to script directory
cd "$(dirname "$0")"

echo "======================================================================"
echo "  USeP OBE Syllabus-to-Class Record Generator - Local Server Launcher"
echo "======================================================================"
echo ""

# Detect Python
PYTHON_EXE=""
if [ -f ".venv/bin/python" ]; then
    PYTHON_EXE=".venv/bin/python"
    echo "[*] Using virtual environment (.venv)"
elif [ -f "venv/bin/python" ]; then
    PYTHON_EXE="venv/bin/python"
    echo "[*] Using virtual environment (venv)"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_EXE="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_EXE="python"
else
    echo "[ERROR] Python was not found on your system!"
    echo "Please install Python 3.10 or newer."
    exit 1
fi

# Check dependencies
echo "[*] Verifying core Python dependencies..."
if ! "$PYTHON_EXE" -c "import flask, werkzeug, pandas, openpyxl, fpdf, pypdf, requests" >/dev/null 2>&1; then
    echo "[!] Missing dependencies detected. Installing from requirements.txt..."
    "$PYTHON_EXE" -m pip install -r requirements.txt
fi
echo "[*] All core dependencies verified."

echo ""
echo "[*] Launching local server on 0.0.0.0 ..."
"$PYTHON_EXE" app.py

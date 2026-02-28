#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────
#  ExamAI Backend — One-Command Start Script (Linux / macOS)
#  Usage:  chmod +x start.sh && ./start.sh
# ─────────────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"

# ── Check .env ──────────────────────────────────────────────────
if [ ! -f ".env" ]; then
    echo "[!] .env file not found."
    echo "    Copy .env.example to .env and fill in your credentials:"
    echo "      cp .env.example .env"
    exit 1
fi

# ── Create virtual environment if missing ───────────────────────
if [ ! -d "venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv venv
fi

# ── Activate venv ───────────────────────────────────────────────
source venv/bin/activate

# ── Install / upgrade dependencies ─────────────────────────────
echo "[*] Installing dependencies..."
pip install -r requirements.txt --quiet

# ── Start the server ────────────────────────────────────────────
echo ""
echo "==================================================="
echo "  ExamAI Backend running at http://localhost:8000"
echo "  API docs at        http://localhost:8000/docs"
echo "  Press Ctrl+C to stop"
echo "==================================================="
echo ""
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

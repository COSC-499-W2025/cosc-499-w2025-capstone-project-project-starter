#!/usr/bin/env bash
# Run the FastAPI server for local development.
# From project root: ./run_api.sh
# Then open http://localhost:8000

set -e
cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH:-$PWD/src}:$PWD/src"
echo "Starting API on http://127.0.0.1:8000 (PYTHONPATH=$PYTHONPATH)"
exec python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

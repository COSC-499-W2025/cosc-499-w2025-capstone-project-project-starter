#!/bin/bash
# Start the FastAPI server

# Check if port 8000 is already in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8000 is already in use!"
    echo ""
    echo "Options:"
    echo "  1. Kill existing process: lsof -ti:8000 | xargs kill -9"
    echo "  2. Use different port:    docker compose run --rm -p 8001:8000 backend python -m src.api.app"
    echo ""
    read -p "Kill existing process and continue? (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Killing process on port 8000..."
        lsof -ti:8000 | xargs kill -9 2>/dev/null
        sleep 1
    else
        echo "Exiting. Use a different port or kill the process manually."
        exit 1
    fi
fi

echo "🚀 Starting FastAPI server on http://localhost:8000"
echo "📖 API docs: http://localhost:8000/docs"
echo "Press Ctrl+C to stop"
echo ""

docker compose run --rm -p 8000:8000 backend python -m src.api.app


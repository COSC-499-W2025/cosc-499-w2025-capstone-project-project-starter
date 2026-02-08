#!/bin/bash
# Kill process on a specific port

PORT=${1:-8000}

if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "🔍 Found process on port $PORT:"
    lsof -i :$PORT
    echo ""
    echo "Killing process..."
    lsof -ti:$PORT | xargs kill -9 2>/dev/null
    echo "✅ Port $PORT is now free"
else
    echo "✅ Port $PORT is already free"
fi


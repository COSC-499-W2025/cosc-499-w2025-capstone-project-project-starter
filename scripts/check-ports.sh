#!/bin/bash
# Check what's running on common ports

echo "🔍 Checking common ports..."
echo ""

check_port() {
    local port=$1
    local service=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        local pid=$(lsof -ti:$port)
        local process=$(ps -p $pid -o comm= 2>/dev/null)
        echo "✗ Port $port ($service): IN USE by PID $pid ($process)"
    else
        echo "✓ Port $port ($service): FREE"
    fi
}

check_port 8000 "API Server"
check_port 5432 "PostgreSQL"
check_port 3306 "MySQL"
check_port 27017 "MongoDB"
check_port 6379 "Redis"

echo ""
echo "💡 To kill a process: ./scripts/kill-port.sh <port>"


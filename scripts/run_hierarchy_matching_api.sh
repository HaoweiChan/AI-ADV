#!/bin/bash
# Run the Hierarchy Matching API server

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Set default port
PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

echo "Starting Hierarchy Matching API server..."
echo "Project root: $PROJECT_ROOT"
echo "Host: $HOST"
echo "Port: $PORT"
echo ""

# Check if uvicorn is installed
if ! python -c "import uvicorn" 2>/dev/null; then
    echo "Error: uvicorn is not installed. Run: pip install uvicorn"
    exit 1
fi

# Run the server
python -m uvicorn api.server:app --host "$HOST" --port "$PORT" --reload


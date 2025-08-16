#!/bin/bash
# Linux version of Invoice System Runner
# Equivalent to RUN_SYSTEM.bat for Windows

echo "=== Invoice System Linux Runner ==="
echo "Starting Invoice Parsing System..."
echo ""

# Check if in correct directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
echo "Working directory: $(pwd)"

# Step 1: Setup Python virtual environment
echo ""
echo "Step 1: Setting up Python virtual environment..."

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment"
        echo "Please ensure Python 3 is installed: sudo apt install python3 python3-venv"
        exit 1
    fi
fi

# Don't activate, just use venv/bin/python directly
echo "Using virtual environment at venv/bin/python"

# Step 2: Install dependencies
echo ""
echo "Step 2: Installing dependencies..."

# Upgrade pip
venv/bin/python -m pip install --upgrade pip --quiet

# Install Python dependencies
if [ -f "requirements.txt" ]; then
    echo "Installing Python dependencies from requirements.txt..."
    venv/bin/python -m pip install -r requirements.txt --quiet
fi

# Install FastAPI and related packages (ensure they're available)
echo "Installing core dependencies..."
venv/bin/python -m pip install fastapi uvicorn --quiet

# Install Node.js dependencies for frontend
echo "Installing Node.js dependencies..."
if [ -d "frontend" ]; then
    cd frontend
    if command -v npm >/dev/null 2>&1; then
        npm install --silent
        echo "Frontend dependencies installed"
    else
        echo "WARNING: npm not found. Please install Node.js"
        echo "Ubuntu/Debian: sudo apt install nodejs npm"
    fi
    cd ..
else
    echo "WARNING: frontend directory not found"
fi

# Step 3: Initialize database
echo ""
echo "Step 3: Initializing database..."

echo "Initializing database with proper virtual environment..."
venv/bin/python -c "
import sys
sys.path.insert(0, '.')
try:
    from database_schema import ParserDatabase
    db = ParserDatabase()
    db.initialize_default_configs()
    print('Database initialized successfully')
except Exception as e:
    print(f'Database initialization error: {e}')
    import traceback
    traceback.print_exc()
"

# Step 4: Start services
echo ""
echo "Step 4: Starting services..."

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping services..."
    pkill -f "uvicorn api_server:app" 2>/dev/null
    pkill -f "npm start" 2>/dev/null
    echo "Services stopped"
}

trap cleanup EXIT

# Start FastAPI backend
echo "Starting FastAPI backend on port 8000..."
cd "$(dirname "$0")"
PYTHONPATH=. venv/bin/python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait a moment for API to start
sleep 3

# Start React frontend
echo "Starting React frontend on port 3000..."
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "=== Services Started ==="
echo "API Server: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Keep script running
wait
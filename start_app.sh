#!/bin/bash

# Simple Invoice Parser - Startup Script
# This script sets up and runs the simplified invoice parser system

echo "=========================================="
echo "    Simple Invoice Parser v2.0"
echo "=========================================="

# Set working directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/Update Python dependencies
echo "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q fastapi uvicorn python-multipart pdfplumber pandas openpyxl

# Check if database exists and has required tables
echo "Checking database..."
python3 -c "
import sqlite3
conn = sqlite3.connect('test_customers.db')
cursor = conn.cursor()

# Check if customer_field_mappings table exists
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='customer_field_mappings'\")
if not cursor.fetchone():
    print('Creating customer_field_mappings table...')
    cursor.execute('''
    CREATE TABLE customer_field_mappings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id TEXT NOT NULL,
        parsed_text TEXT NOT NULL,
        field_type TEXT NOT NULL,
        mapped_value TEXT,
        description TEXT,
        active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    print('Table created successfully')

# Check customer count
cursor.execute('SELECT COUNT(*) FROM customers WHERE active = 1')
count = cursor.fetchone()[0]
print(f'Database ready with {count} customers')
conn.close()
"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Please install Node.js to run the frontend."
    echo "Visit https://nodejs.org/"
    exit 1
fi

# Install frontend dependencies if needed
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Start the services
echo ""
echo "Starting services..."
echo "=========================================="

# Kill any existing processes on our ports
pkill -f "uvicorn api_server:app" 2>/dev/null
pkill -f "npm start" 2>/dev/null
sleep 2

# Start API server in background
echo "Starting API server on http://localhost:8001"
nohup python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8001 --reload > api.log 2>&1 &
API_PID=$!

# Start React frontend in background
echo "Starting frontend on http://localhost:3000"
cd frontend
nohup npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait a moment for services to start
sleep 3

# Check if services are running
if ps -p $API_PID > /dev/null; then
    echo "✓ API server is running (PID: $API_PID)"
else
    echo "✗ API server failed to start. Check api.log for details"
fi

if ps -p $FRONTEND_PID > /dev/null; then
    echo "✓ Frontend is running (PID: $FRONTEND_PID)"
else
    echo "✗ Frontend failed to start. Check frontend.log for details"
fi

echo ""
echo "=========================================="
echo "System is ready!"
echo ""
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "How to use:"
echo "1. Go to http://localhost:3000"
echo "2. Click 'Customer Mappings' to define what parsed text means"
echo "3. Click 'Parse Invoice' to test with PDF files"
echo ""
echo "To stop the system, run: ./stop_app.sh"
echo "=========================================="

# Keep script running and show logs
echo ""
echo "Press Ctrl+C to stop the services..."
tail -f api.log frontend.log
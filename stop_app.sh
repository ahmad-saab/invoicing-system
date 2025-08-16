#!/bin/bash

# Stop the Simple Invoice Parser services

echo "Stopping Simple Invoice Parser services..."

# Kill API server
pkill -f "uvicorn api_server:app"
echo "✓ API server stopped"

# Kill React frontend
pkill -f "npm start"
pkill -f "react-scripts start"
echo "✓ Frontend stopped"

# Clean up any node processes
pkill -f "node.*frontend"

echo "All services stopped."
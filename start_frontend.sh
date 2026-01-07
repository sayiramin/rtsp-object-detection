#!/bin/bash

# Start Frontend Server
echo "🌐 Starting React Frontend..."
echo "📍 Location: $(pwd)/frontend"

# Check if node_modules exists
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing dependencies..."
    cd frontend && npm install && cd ..
fi

# Start frontend
echo "🚀 Starting frontend server on port 3000..."
cd frontend
BROWSER=none npm start

echo "🛑 Frontend stopped."

#!/bin/bash

# RTSP Object Detection System Startup Script

echo "🚀 Starting RTSP Object Detection System..."

# Check if RTSP streamer is running
echo "📡 Checking RTSP stream availability..."
if ! curl -s --connect-timeout 3 rtsp://localhost:8554/stream > /dev/null 2>&1; then
    echo "⚠️  RTSP stream not detected at rtsp://localhost:8554/stream"
    echo "   Please start your webcam RTSP streamer first:"
    echo "   cd ../webcam-rtsp-streamer && source venv/bin/activate && python src/main.py"
    echo ""
fi

# Start backend in background
echo "🔧 Starting backend server..."
cd "$(dirname "$0")"
source venv/bin/activate
python -m backend.main &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
echo "🌐 Starting frontend..."
cd frontend
npm start &
FRONTEND_PID=$!

echo ""
echo "✅ System started!"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   Video Stream: ws://localhost:8000/ws/video"
echo "   Alerts: ws://localhost:8000/ws/alerts"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user interrupt
trap 'echo "🛑 Stopping services..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit' INT
wait

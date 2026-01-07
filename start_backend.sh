#!/bin/bash

# RTSP Object Detection System - Complete Startup Script

echo "🚀 Starting RTSP Object Detection System..."
echo "📍 Location: $(pwd)"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if RTSP stream is available
echo "📡 Checking RTSP stream..."
if timeout 3s ffprobe rtsp://localhost:8554/stream >/dev/null 2>&1; then
    echo "✅ RTSP stream is available"
else
    echo "⚠️  RTSP stream not detected. Make sure webcam streamer is running."
    echo "   Start with: cd ../webcam-rtsp-streamer && source venv/bin/activate && python src/main.py"
fi

# Start backend
echo "🔧 Starting backend server on port 8002..."
python backend/main.py

echo "🛑 Backend stopped."

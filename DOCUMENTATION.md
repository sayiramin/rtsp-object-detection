# RTSP Object Detection System - Documentation

## Overview
Real-time object detection system that processes RTSP video streams to detect people, headgear compliance, zone violations, and movement patterns.

## Features
- 🎥 **Real-time RTSP Stream Processing**
- 👤 **Person Detection** with YOLOv8
- 🎩 **Headgear Detection** (caps, hoodies, hats vs hair/bald)
- 🚫 **Interactive Zone Drawing** and monitoring
- 🚶 **Movement Detection** (walking detection)
- 🔔 **Live Alert System** with WebSocket notifications
- 🌐 **Modern Web Interface** with React

## System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   RTSP Stream   │───▶│  Python Backend │───▶│ React Frontend  │
│  (Webcam Feed)  │    │   (Detection)   │    │ (Web Interface) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   YOLOv8 Model  │
                       │ Object Detection │
                       └─────────────────┘
```

## Quick Start

### Prerequisites
1. **RTSP Stream**: Webcam RTSP streamer running on `rtsp://localhost:8554/stream`
2. **Python 3.8+** and **Node.js 16+**
3. **FFmpeg** and **MediaMTX** installed

### Installation
```bash
# 1. Clone and setup backend
cd rtsp-object-detection
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Setup frontend
cd frontend
npm install

# 3. Start system
# Terminal 1: Backend
cd rtsp-object-detection
source venv/bin/activate
python backend/main.py

# Terminal 2: Frontend
cd rtsp-object-detection/frontend
npm start
```

### Access
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8002
- **Health Check**: http://localhost:8002/health

## Usage Guide

### 1. Headgear Detection
- **Green Box + "HEAD COVERED"**: Person wearing cap, hoodie, hat, helmet
- **Red Box + "NO HEAD COVER"**: Person with only hair or bald head
- **Alerts**: Triggered when no head protection detected

### 2. Zone Drawing
1. Enter zone ID (e.g., "restricted-area-1")
2. Click "🎯 Draw Zone"
3. Click on video to add points (minimum 3)
4. Double-click to finish zone
5. Zone appears as red overlay with label

### 3. Live Monitoring
- **Video Stream**: Shows live feed with detection overlays
- **Zone Overlays**: Red transparent areas with labels
- **Live Alerts**: Real-time notifications in right panel
- **System Status**: Shows connection and system health

### 4. Alert Types
- **⚠️ SAFETY ALERT**: Person without head protection
- **🚨 INTRUSION ALERT**: Person in restricted zone
- **🚶 MOVEMENT DETECTED**: Person walking (optional)

## API Endpoints

### REST API
- `GET /health` - System health check
- `GET /api/status` - System status and zones
- `POST /api/zones` - Add monitoring zone
- `DELETE /api/zones/{zone_id}` - Remove zone

### WebSocket Endpoints
- `ws://localhost:8002/ws/video` - Live video stream
- `ws://localhost:8002/ws/alerts` - Real-time alerts

## Configuration

### Detection Settings
- **Confidence Threshold**: 0.5 (50%)
- **Frame Rate**: 10 FPS
- **Video Resolution**: Max 800px width
- **Alert History**: Last 100 alerts

### Headgear Detection
- **Head Region**: Top 20% of person bounding box
- **Fabric Detection**: Color-based analysis for manufactured items
- **Threshold**: 40% fabric coverage = head covered

### Zone Detection
- **Algorithm**: Point-in-polygon ray casting
- **Accuracy**: Checks person center position
- **Real-time**: Immediate alert on violation

## File Structure

```
rtsp-object-detection/
├── backend/
│   ├── main.py              # Main backend server
│   └── __init__.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── VideoStream.tsx    # Video display + zone drawing
│   │   │   └── Alerts.tsx         # Alert notifications
│   │   ├── App.tsx               # Main application
│   │   └── App.css              # Styling
│   └── package.json
├── requirements.txt         # Python dependencies
├── README.md               # This documentation
└── start_backend.sh        # Backend startup script
```

## Troubleshooting

### Common Issues

1. **"System Stopped" Status**
   - Check RTSP stream: `ffprobe rtsp://localhost:8554/stream`
   - Restart webcam RTSP streamer
   - Check backend logs

2. **"Live Alerts Disconnected"**
   - Refresh browser page
   - Check WebSocket connection in browser console
   - Restart backend server

3. **Zone Drawing Inaccurate**
   - Ensure browser is not zoomed
   - Use full-screen mode for better accuracy
   - Check browser console for coordinate logs

4. **Headgear Detection Issues**
   - Ensure good lighting conditions
   - Person should be clearly visible
   - Head region should be unobstructed

### Performance Optimization
- **Reduce Resolution**: Modify max width in backend
- **Lower Frame Rate**: Increase sleep time in video WebSocket
- **GPU Acceleration**: Install CUDA-enabled PyTorch

## Development

### Adding New Features
1. **New Alert Types**: Modify `check_alerts()` function
2. **Detection Improvements**: Update `detect_objects()` function
3. **UI Changes**: Modify React components in `frontend/src/`

### Testing
- **Backend**: `curl http://localhost:8002/health`
- **WebSocket**: Browser console network tab
- **Zones**: Draw test zones and walk through them

## Support
- Check browser console for errors
- Review backend logs for detection issues
- Ensure all dependencies are installed
- Verify RTSP stream is working

## License
MIT License - Free to use and modify.

# RTSP Object Detection System

A real-time object detection system that processes RTSP video streams to detect people, headgear compliance, zone violations, and object carrying behavior.

## Features

- 🎥 **Real-time RTSP Stream Processing** - Captures and processes video from RTSP sources
- 👤 **Person Detection** - Uses YOLOv8 for accurate person detection
- 🎩 **Headgear Detection** - Custom algorithm to detect headgear compliance
- 🚫 **Zone Monitoring** - Configurable restricted areas with polygon drawing
- 🪑 **Object Carrying Detection** - Detects people carrying chairs or other objects
- 🔔 **Live Alerts** - Real-time alert system with WebSocket notifications
- 🌐 **Web Interface** - Modern React frontend with live video feed
- ⚙️ **Configuration Panel** - Easy zone setup and system monitoring

## Architecture

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

1. **RTSP Stream**: Make sure your webcam RTSP streamer is running
   ```bash
   cd ../webcam-rtsp-streamer
   source venv/bin/activate
   python src/main.py
   ```

2. **Python 3.8+** and **Node.js 16+** installed

### Installation & Setup

1. **Install Python dependencies**:
   ```bash
   cd rtsp-object-detection
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Install Frontend dependencies**:
   ```bash
   cd frontend
   npm install
   ```

3. **Start the complete system**:
   ```bash
   ./start.sh
   ```

   Or start components individually:
   
   **Backend**:
   ```bash
   source venv/bin/activate
   python -m backend.main
   ```
   
   **Frontend**:
   ```bash
   cd frontend
   npm start
   ```

## Usage

1. **Access the Web Interface**: Open http://localhost:3000
2. **View Live Feed**: The main panel shows the live video with detection overlays
3. **Monitor Alerts**: Right panel displays real-time alerts and notifications
4. **Configure Zones**: Add restricted areas using the zone configuration panel
5. **System Status**: Header shows system running status and connection health

## API Endpoints

### REST API
- `GET /api/status` - Get system status and configuration
- `POST /api/zones` - Add a new monitoring zone
- `DELETE /api/zones/{zone_id}` - Remove a monitoring zone

### WebSocket Endpoints
- `ws://localhost:8000/ws/video` - Live video stream with detection overlays
- `ws://localhost:8000/ws/alerts` - Real-time alert notifications

## Configuration

### Detection Settings
- **Confidence Threshold**: Adjust in `backend/object_detector.py`
- **Headgear Sensitivity**: Modify in `backend/headgear_detector.py`
- **RTSP URL**: Change in `backend/detection_pipeline.py`

### Alert Types
- `no_headgear` - Person detected without required headgear
- `zone_violation` - Person entered restricted zone
- `carrying_chair` - Person detected carrying chairs

## Development

### Backend Structure
```
backend/
├── rtsp_streamer.py      # RTSP stream capture
├── object_detector.py    # YOLOv8 object detection
├── headgear_detector.py  # Custom headgear detection
├── zone_monitor.py       # Zone violation monitoring
├── detection_pipeline.py # Main processing pipeline
└── main.py              # FastAPI server
```

### Frontend Structure
```
frontend/src/
├── components/
│   ├── VideoStream.tsx   # Live video display
│   ├── Alerts.tsx        # Alert notifications
│   └── ZoneConfig.tsx    # Zone configuration
├── App.tsx              # Main application
└── App.css              # Styling
```

## Troubleshooting

### Common Issues

1. **RTSP Connection Failed**
   - Ensure webcam RTSP streamer is running on `rtsp://localhost:8554/stream`
   - Check network connectivity and firewall settings

2. **No Video Display**
   - Verify WebSocket connection in browser developer tools
   - Check backend logs for RTSP stream errors

3. **Detection Not Working**
   - YOLOv8 model downloads automatically on first run
   - Ensure sufficient system resources (CPU/GPU)

4. **Frontend Not Loading**
   - Run `npm install` in frontend directory
   - Check for port conflicts (default: 3000)

### Performance Optimization

- **Reduce Frame Rate**: Modify sleep time in detection pipeline
- **Lower Resolution**: Adjust video capture settings
- **GPU Acceleration**: Install CUDA-enabled PyTorch for faster inference

## License

MIT License - Feel free to use and modify for your projects.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

For issues or feature requests, please open an issue on the repository.

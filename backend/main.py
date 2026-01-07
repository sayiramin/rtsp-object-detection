from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import cv2
import json
import asyncio
import base64
import numpy as np
import time
import os
from datetime import datetime
from typing import List
from ultralytics import YOLO

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

manager = ConnectionManager()

# Global variables
model = None
cap = None
alerts = []
zones = {}
previous_positions = {}  # Track person positions for movement detection
previous_chair_positions = {}  # Track chair positions for movement detection
photos_dir = "captured_photos"  # Directory for saved photos

def init_system():
    global model, cap
    try:
        print("Loading YOLO model...")
        model = YOLO('yolov8n.pt')
        print("✅ YOLO model loaded")
        
        print("Connecting to RTSP stream...")
        cap = cv2.VideoCapture("rtsp://localhost:8554/stream")
        if cap.isOpened():
            print("✅ RTSP stream connected")
            return True
        else:
            print("❌ RTSP stream failed")
            return False
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        return False

def detect_headgear(frame, person_bbox):
    """Detect if head is covered with cap, hat, hoodie, etc. (NOT just hair)"""
    x1, y1, x2, y2 = person_bbox
    
    # Extract head region (top 20% of person bbox)
    head_height = int((y2 - y1) * 0.2)
    if head_height < 10:  # Too small
        return False
        
    head_region = frame[y1:y1 + head_height, x1:x2]
    
    if head_region.size == 0:
        return False
    
    # Convert to HSV
    hsv = cv2.cvtColor(head_region, cv2.COLOR_BGR2HSV)
    
    # Define fabric/manufactured item colors (caps, hoodies, hats)
    fabric_colors = [
        ([0, 0, 0], [180, 255, 50]),      # Black/dark items
        ([100, 50, 50], [130, 255, 255]), # Blue items
        ([0, 50, 50], [20, 255, 255]),    # Red items
        ([40, 50, 50], [80, 255, 255]),   # Green items
        ([0, 0, 200], [180, 30, 255]),    # White/light items
    ]
    
    total_pixels = head_region.shape[0] * head_region.shape[1]
    fabric_pixels = 0
    
    # Count fabric-like colored pixels
    for (lower, upper) in fabric_colors:
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        fabric_pixels += cv2.countNonZero(mask)
    
    fabric_ratio = fabric_pixels / total_pixels
    
    # If more than 40% of head region has fabric-like colors = covered
    is_covered = fabric_ratio > 0.4
    
    print(f"Head coverage check: fabric_ratio={fabric_ratio:.2f}, covered={is_covered}")
    return is_covered

def save_detection_photo(frame, alert_type, description):
    """Save photo when chair movement is detected"""
    try:
        # Create photos directory if it doesn't exist
        os.makedirs(photos_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{alert_type}_{timestamp}.jpg"
        filepath = os.path.join(photos_dir, filename)
        
        # Add text overlay with detection info
        overlay_frame = frame.copy()
        
        # Add timestamp and description
        text_lines = [
            f"DETECTION: {description}",
            f"TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"ALERT: {alert_type.upper()}"
        ]
        
        y_offset = 30
        for line in text_lines:
            cv2.putText(overlay_frame, line, (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            y_offset += 30
        
        # Save the photo
        success = cv2.imwrite(filepath, overlay_frame)
        
        if success:
            print(f"📸 PHOTO SAVED: {filepath}")
            return filepath
        else:
            print(f"❌ Failed to save photo: {filepath}")
            return None
            
    except Exception as e:
        print(f"❌ Error saving photo: {e}")
        return None
    """Detect dominant clothing color of person"""
    x1, y1, x2, y2 = person_bbox
    
    # Extract torso region (middle 60% of person bbox, skip head)
    height = y2 - y1
    torso_start = y1 + int(height * 0.2)  # Skip head
    torso_end = y1 + int(height * 0.8)    # Skip legs
    torso_region = frame[torso_start:torso_end, x1:x2]
    
    if torso_region.size == 0:
        return "Unknown"
    
    # Convert to HSV for better color analysis
    hsv = cv2.cvtColor(torso_region, cv2.COLOR_BGR2HSV)
    
    # Define color ranges
    color_ranges = {
        'Red': ([0, 50, 50], [10, 255, 255]),
        'Blue': ([100, 50, 50], [130, 255, 255]),
        'Green': ([40, 50, 50], [80, 255, 255]),
        'Yellow': ([20, 50, 50], [30, 255, 255]),
        'Black': ([0, 0, 0], [180, 255, 50]),
        'White': ([0, 0, 200], [180, 30, 255]),
        'Purple': ([130, 50, 50], [160, 255, 255]),
    }
    
    max_pixels = 0
    dominant_color = "Unknown"
    
    for color_name, (lower, upper) in color_ranges.items():
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        pixel_count = cv2.countNonZero(mask)
        
        if pixel_count > max_pixels:
            max_pixels = pixel_count
            dominant_color = color_name
    
    return dominant_color

def detect_clothing_color(frame, person_bbox):
    """Detect dominant clothing color of person"""
    x1, y1, x2, y2 = person_bbox
    
    # Extract torso region (middle 60% of person bbox, skip head)
    height = y2 - y1
    torso_start = y1 + int(height * 0.2)  # Skip head
    torso_end = y1 + int(height * 0.8)    # Skip legs
    torso_region = frame[torso_start:torso_end, x1:x2]
    
    if torso_region.size == 0:
        return "Unknown"
    
    # Convert to HSV for better color analysis
    hsv = cv2.cvtColor(torso_region, cv2.COLOR_BGR2HSV)
    
    # Define color ranges
    color_ranges = {
        'Red': ([0, 50, 50], [10, 255, 255]),
        'Blue': ([100, 50, 50], [130, 255, 255]),
        'Green': ([40, 50, 50], [80, 255, 255]),
        'Yellow': ([20, 50, 50], [30, 255, 255]),
        'Black': ([0, 0, 0], [180, 255, 50]),
        'White': ([0, 0, 200], [180, 30, 255]),
        'Purple': ([130, 50, 50], [160, 255, 255]),
    }
    
    max_pixels = 0
    dominant_color = "Unknown"
    
    for color_name, (lower, upper) in color_ranges.items():
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        pixel_count = cv2.countNonZero(mask)
        
        if pixel_count > max_pixels:
            max_pixels = pixel_count
            dominant_color = color_name
    
    return dominant_color

def detect_real_chair_movement(chair_id, current_center, current_bbox):
    """Detect actual chair movement with improved noise filtering"""
    global previous_chair_positions
    
    if chair_id not in previous_chair_positions:
        previous_chair_positions[chair_id] = {
            'positions': [current_center],
            'last_moved': 0
        }
        return False
    
    prev_data = previous_chair_positions[chair_id]
    positions = prev_data['positions']
    
    # Add current position
    positions.append(current_center)
    
    # Keep only last 12 positions for analysis
    if len(positions) > 12:
        positions = positions[-12:]
    
    # Need at least 8 positions to determine real movement
    if len(positions) < 8:
        previous_chair_positions[chair_id]['positions'] = positions
        return False
    
    # Calculate movement using median filtering to reduce noise
    # Compare first 4 vs last 4 positions
    first_quarter = positions[:4]
    last_quarter = positions[-4:]
    
    # Calculate average positions
    first_avg = [sum(p[0] for p in first_quarter) / 4, sum(p[1] for p in first_quarter) / 4]
    last_avg = [sum(p[0] for p in last_quarter) / 4, sum(p[1] for p in last_quarter) / 4]
    
    # Calculate displacement
    displacement = np.sqrt((last_avg[0] - first_avg[0])**2 + (last_avg[1] - first_avg[1])**2)
    
    # Update stored data
    previous_chair_positions[chair_id] = {
        'positions': positions,
        'last_moved': time.time() if displacement > 25 else prev_data['last_moved']
    }
    
    # Real movement requires significant displacement (25+ pixels) over time
    is_moving = displacement > 25
    if is_moving:
        print(f"🪑 CONFIRMED CHAIR MOVEMENT: Chair {chair_id} displaced {displacement:.1f} pixels")
    
    return is_moving

def detect_person_near_chair(person_bbox, chair_bbox):
    """Check if person is near chair for interaction"""
    px1, py1, px2, py2 = person_bbox
    cx1, cy1, cx2, cy2 = chair_bbox
    
    person_center = ((px1 + px2) // 2, (py1 + py2) // 2)
    chair_center = ((cx1 + cx2) // 2, (cy1 + cy2) // 2)
    
    distance = np.sqrt((person_center[0] - chair_center[0])**2 + (person_center[1] - chair_center[1])**2)
    return distance < 120  # Within 120 pixels
    """Detect if person is walking/moving"""
    global previous_positions
    
    if person_id not in previous_positions:
        previous_positions[person_id] = current_center
        return False
    
    prev_center = previous_positions[person_id]
    distance = np.sqrt((current_center[0] - prev_center[0])**2 + (current_center[1] - prev_center[1])**2)
    
    # Update position
    previous_positions[person_id] = current_center
    
    # If moved more than 20 pixels, consider as walking
    return distance > 20

def detect_movement(person_id, current_center):
    """Detect if person is walking/moving"""
    global previous_positions
    
    if person_id not in previous_positions:
        previous_positions[person_id] = current_center
        return False
    
    prev_center = previous_positions[person_id]
    distance = np.sqrt((current_center[0] - prev_center[0])**2 + (current_center[1] - prev_center[1])**2)
    
    # Update position
    previous_positions[person_id] = current_center
    
    # If moved more than 20 pixels, consider as walking
    return distance > 20

def detect_objects(frame):
    if model is None:
        return frame, []
    
    try:
        results = model(frame, conf=0.5)
        detections = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    conf = float(box.conf[0].cpu().numpy())
                    cls = int(box.cls[0].cpu().numpy())
                    class_name = model.names[cls]
                    center = ((x1 + x2) // 2, (y1 + y2) // 2)
                    
                    detection = {
                        'bbox': [x1, y1, x2, y2],
                        'confidence': conf,
                        'class': cls,
                        'class_name': class_name,
                        'center': center
                    }
                    
                    # Enhanced person detection with clothing color
                    if class_name == 'person':
                        try:
                            clothing_color = detect_clothing_color(frame, [x1, y1, x2, y2])
                            is_walking = detect_movement(f"person_{i}", center)
                            detection['clothing_color'] = clothing_color
                            detection['is_walking'] = is_walking
                            
                            color = (0, 255, 0)  # Green for person
                            label = f"PERSON: {conf:.2f} - {clothing_color}"
                            if is_walking:
                                label += " - WALKING"
                        except Exception as e:
                            print(f"Person detection error: {e}")
                            detection['clothing_color'] = "Unknown"
                            detection['is_walking'] = False
                            color = (0, 255, 0)
                            label = f"PERSON: {conf:.2f}"
                    
                    # Real chair movement detection
                    elif class_name == 'chair':
                        try:
                            is_moving = detect_real_chair_movement(f"chair_{i}", center, [x1, y1, x2, y2])
                            detection['is_moving'] = is_moving
                            
                            if is_moving:
                                # Check for people nearby
                                people_nearby = []
                                for other_det in detections:
                                    if other_det['class_name'] == 'person':
                                        if detect_person_near_chair(other_det['bbox'], [x1, y1, x2, y2]):
                                            people_nearby.append(other_det)
                                detection['people_nearby'] = people_nearby
                                
                                color = (0, 255, 255)  # Yellow for moving chair
                                label = f"CHAIR: {conf:.2f} - MOVING"
                            else:
                                color = (255, 0, 0)  # Blue for stationary chair
                                label = f"CHAIR: {conf:.2f} - STATIONARY"
                        except Exception as e:
                            print(f"Chair movement detection error: {e}")
                            detection['is_moving'] = False
                            color = (255, 0, 0)
                            label = f"CHAIR: {conf:.2f}"
                    
                    else:
                        color = (255, 0, 0)  # Blue for other objects
                        label = f"{class_name}: {conf:.2f}"
                    
                    # Draw bounding box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                    
                    # Draw label with background
                    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                    cv2.rectangle(frame, (x1, y1 - label_size[1] - 10), 
                                (x1 + label_size[0], y1), color, -1)
                    cv2.putText(frame, label, (x1, y1 - 5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                    detections.append(detection)
        
        moving_chairs = [d for d in detections if d['class_name'] == 'chair' and d.get('is_moving', False)]
        print(f"🎯 Detected {len(detections)} objects, {len(moving_chairs)} moving chairs")
        return frame, detections
        
    except Exception as e:
        print(f"Detection error: {e}")
        return frame, []

def check_alerts(detections, current_frame):
    global alerts
    import time
    
    # Generate alerts for ANY chair movement
    for detection in detections:
        if detection['class_name'] == 'chair' and detection.get('is_moving', False):
            # Chair movement detected
            bbox = [int(x) for x in detection['bbox']]
            confidence = float(detection['confidence'])
            
            # Check if person is nearby for context
            people_nearby = detection.get('people_nearby', [])
            person_clothing = "Unknown"
            if people_nearby:
                person_clothing = people_nearby[0].get('clothing_color', 'Unknown')
            
            # Save photo of the detection
            description = f"Chair moved - Person nearby: {person_clothing if people_nearby else 'None'}"
            photo_path = save_detection_photo(current_frame, "chair_moved", description)
            
            alerts.append({
                'type': 'chair_moved',
                'timestamp': float(time.time()),
                'bbox': bbox,
                'confidence': confidence,
                'message': f'🪑 CHAIR MOVED: {person_clothing + " nearby" if people_nearby else "No person visible"}',
                'photo_path': photo_path
            })
            print(f"✅ CHAIR MOVED + PHOTO: {person_clothing + ' nearby' if people_nearby else 'No person visible'}")
    
    # Keep last 50 alerts and sort by timestamp (newest first)
    alerts = sorted(alerts[-50:], key=lambda x: x['timestamp'], reverse=True)

def point_in_polygon(point, polygon):
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside

def draw_zones(frame):
    for zone_id, points in zones.items():
        if len(points) >= 3:
            pts = np.array(points, np.int32)
            pts = pts.reshape((-1, 1, 2))
            
            # Draw filled polygon with transparency
            overlay = frame.copy()
            cv2.fillPoly(overlay, [pts], (0, 0, 255))
            cv2.addWeighted(frame, 0.8, overlay, 0.2, 0, frame)
            
            # Draw border
            cv2.polylines(frame, [pts], True, (0, 0, 255), 3)
            
            # Add zone label with background
            label = f"RESTRICTED: {zone_id}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            label_pos = tuple(points[0])
            
            # Background rectangle for text
            cv2.rectangle(frame, 
                         (label_pos[0], label_pos[1] - label_size[1] - 5),
                         (label_pos[0] + label_size[0], label_pos[1] + 5),
                         (0, 0, 255), -1)
            
            cv2.putText(frame, label, label_pos, 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    return frame

# Initialize system
init_system()

@app.get("/")
async def root():
    return {"message": "RTSP Object Detection System", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "rtsp_connected": cap is not None and cap.isOpened(),
        "websocket_connections": len(manager.active_connections),
        "zones_count": len(zones),
        "alerts_count": len(alerts)
    }

@app.get("/api/photos")
async def list_photos():
    """List all captured photos"""
    try:
        if not os.path.exists(photos_dir):
            return {"photos": []}
        
        photos = []
        for filename in os.listdir(photos_dir):
            if filename.endswith('.jpg'):
                filepath = os.path.join(photos_dir, filename)
                stat = os.stat(filepath)
                photos.append({
                    'filename': filename,
                    'timestamp': stat.st_mtime,
                    'size': stat.st_size,
                    'path': filepath
                })
        
        # Sort by timestamp (newest first)
        photos.sort(key=lambda x: x['timestamp'], reverse=True)
        return {"photos": photos}
    except Exception as e:
        print(f"Error listing photos: {e}")
        return {"photos": []}
async def get_status():
    return {
        "pipeline_running": True,
        "zones": [],
        "recent_alerts": []
    }

@app.post("/api/zones")
async def add_zone(zone_data: dict):
    zone_id = zone_data.get('id')
    points = zone_data.get('points', [])
    
    if zone_id and len(points) >= 3:
        zones[zone_id] = points
        print(f"✅ Zone added: {zone_id} with {len(points)} points: {points}")
        return {"status": "success", "message": f"Zone {zone_id} added successfully"}
    else:
        return {"status": "error", "message": "Invalid zone data - need at least 3 points"}

@app.delete("/api/zones/{zone_id}")
async def remove_zone(zone_id: str):
    if zone_id in zones:
        del zones[zone_id]
        print(f"✅ Zone removed: {zone_id}")
        return {"status": "success", "message": f"Zone {zone_id} removed successfully"}
    else:
        return {"status": "error", "message": f"Zone {zone_id} not found"}

@app.websocket("/ws/video")
async def websocket_video(websocket: WebSocket):
    await manager.connect(websocket)
    print("✅ Video WebSocket client connected")
    
    try:
        while True:
            if cap and cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    print("📹 Processing frame...")
                    
                    # Run detection and draw bounding boxes
                    frame_with_detections, detections = detect_objects(frame)
                    
                    # Draw zones if any
                    frame_with_detections = draw_zones(frame_with_detections)
                    
                    # Generate alerts with photo capture
                    if detections:
                        check_alerts(detections, frame_with_detections)
                        print(f"🎯 Frame processed with {len(detections)} detections")
                    
                    # Resize for performance but keep quality
                    height, width = frame_with_detections.shape[:2]
                    if width > 800:
                        scale = 800 / width
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        frame_with_detections = cv2.resize(frame_with_detections, (new_width, new_height))
                    
                    # Encode with good quality to see bounding boxes clearly
                    _, buffer = cv2.imencode('.jpg', frame_with_detections, [cv2.IMWRITE_JPEG_QUALITY, 90])
                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                    
                    await websocket.send_text(json.dumps({
                        'type': 'frame',
                        'data': frame_base64,
                        'detections': len(detections),
                        'zones': len(zones)
                    }))
                else:
                    await websocket.send_text(json.dumps({
                        'type': 'error',
                        'message': 'Failed to read frame'
                    }))
            else:
                await websocket.send_text(json.dumps({
                    'type': 'error',
                    'message': 'RTSP stream not available'
                }))
            
            await asyncio.sleep(0.1)  # 10 FPS
    except WebSocketDisconnect:
        print("❌ Video WebSocket client disconnected")
        manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ Video WebSocket error: {e}")
        manager.disconnect(websocket)

@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await manager.connect(websocket)
    print("✅ Alerts WebSocket client connected")
    last_alert_count = 0
    
    try:
        # Send immediate connection confirmation
        await websocket.send_text(json.dumps({
            'type': 'connection_status',
            'status': 'connected',
            'message': 'Live alerts system connected successfully'
        }))
        print("📤 Sent connection confirmation")
        
        # Send a test alert immediately
        await websocket.send_text(json.dumps({
            'type': 'alerts',
            'data': [{
                'type': 'system_ready',
                'timestamp': float(time.time()),
                'message': '🚀 Alert system is ready and working!'
            }]
        }))
        print("📤 Sent test alert")
        
        while True:
            current_alert_count = len(alerts)
            if current_alert_count > last_alert_count:
                new_alerts = alerts[last_alert_count:]
                print(f"📢 Sending {len(new_alerts)} new alerts to frontend")
                
                # Convert alerts to JSON-serializable format
                serializable_alerts = []
                for alert in new_alerts:
                    serializable_alert = {
                        'type': str(alert['type']),
                        'timestamp': float(alert['timestamp']),
                        'message': str(alert['message'])
                    }
                    if 'bbox' in alert:
                        serializable_alert['bbox'] = [int(x) for x in alert['bbox']]
                    if 'confidence' in alert:
                        serializable_alert['confidence'] = float(alert['confidence'])
                    if 'zone_id' in alert:
                        serializable_alert['zone_id'] = str(alert['zone_id'])
                    serializable_alerts.append(serializable_alert)
                
                await websocket.send_text(json.dumps({
                    'type': 'alerts',
                    'data': serializable_alerts
                }))
                last_alert_count = current_alert_count
            
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        print("❌ Alerts WebSocket client disconnected")
        manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ Alerts WebSocket error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

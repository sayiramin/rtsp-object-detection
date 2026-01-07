from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import cv2
import json
import asyncio
import base64
import numpy as np
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

def detect_chair_movement(chair_id, current_center):
    """Detect if chair is being moved/pushed"""
    global previous_chair_positions
    
    if chair_id not in previous_chair_positions:
        previous_chair_positions[chair_id] = current_center
        return False
    
    prev_center = previous_chair_positions[chair_id]
    distance = np.sqrt((current_center[0] - prev_center[0])**2 + (current_center[1] - prev_center[1])**2)
    
    # Update position
    previous_chair_positions[chair_id] = current_center
    
    # If chair moved more than 15 pixels, consider as being moved
    return distance > 15

def detect_person_with_chair(person_bbox, chair_bbox):
    """Detect if person is pushing/walking with chair"""
    px1, py1, px2, py2 = person_bbox
    cx1, cy1, cx2, cy2 = chair_bbox
    
    # Calculate centers
    person_center = ((px1 + px2) // 2, (py1 + py2) // 2)
    chair_center = ((cx1 + cx2) // 2, (cy1 + cy2) // 2)
    
    # Calculate distance between person and chair
    distance = np.sqrt((person_center[0] - chair_center[0])**2 + (person_center[1] - chair_center[1])**2)
    
    # If person is within 100 pixels of chair, they're likely interacting with it
    return distance < 100
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
        person_detections = []
        chair_detections = []
        
        # First pass: collect all detections
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    conf = float(box.conf[0].cpu().numpy())
                    cls = int(box.cls[0].cpu().numpy())
                    class_name = model.names[cls]
                    
                    detection = {
                        'bbox': [x1, y1, x2, y2],
                        'confidence': conf,
                        'class': cls,
                        'class_name': class_name,
                        'center': ((x1 + x2) // 2, (y1 + y2) // 2)
                    }
                    
                    if class_name == 'person':
                        person_detections.append((i, detection))
                    elif class_name == 'chair':
                        chair_detections.append((i, detection))
                    
                    detections.append(detection)
        
        # Second pass: analyze person-chair interactions
        chair_movement_pairs = []
        for person_idx, person_det in person_detections:
            # Check headgear and movement for person
            has_headgear = detect_headgear(frame, person_det['bbox'])
            is_walking = detect_movement(f"person_{person_idx}", person_det['center'])
            
            person_det['has_headgear'] = has_headgear
            person_det['is_walking'] = is_walking
            
            # Check if person is with a moving chair
            person_with_chair = False
            chair_moved = False
            
            for chair_idx, chair_det in chair_detections:
                # Check if chair is moving
                chair_is_moving = detect_chair_movement(f"chair_{chair_idx}", chair_det['center'])
                chair_det['is_moving'] = chair_is_moving
                
                # Check if person is near the chair
                if detect_person_with_chair(person_det['bbox'], chair_det['bbox']):
                    if chair_is_moving and is_walking:
                        person_with_chair = True
                        chair_moved = True
                        chair_movement_pairs.append((person_idx, chair_idx))
            
            person_det['with_moving_chair'] = person_with_chair
        
        # Third pass: draw all detections with labels
        for i, detection in enumerate(detections):
            x1, y1, x2, y2 = detection['bbox']
            class_name = detection['class_name']
            conf = detection['confidence']
            
            # Determine color and status
            if class_name == 'person':
                has_headgear = detection.get('has_headgear', False)
                is_walking = detection.get('is_walking', False)
                with_chair = detection.get('with_moving_chair', False)
                
                if with_chair:
                    color = (0, 255, 255)  # Yellow for person moving chair
                    status = "CHAIR MOVED"
                elif has_headgear:
                    color = (0, 255, 0)  # Green for head covered
                    status = "HEAD COVERED"
                else:
                    color = (0, 0, 255)  # Red for no head cover
                    status = "NO HEAD COVER"
                
                if is_walking and not with_chair:
                    status += " - WALKING"
                    
            elif class_name == 'chair':
                is_moving = detection.get('is_moving', False)
                if is_moving:
                    color = (255, 0, 255)  # Magenta for moving chair
                    status = "MOVING"
                else:
                    color = (255, 0, 0)  # Blue for stationary chair
                    status = "STATIONARY"
            else:
                color = (255, 0, 0)  # Blue for other objects
                status = ""
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"{class_name}: {conf:.2f}"
            if status:
                label += f" - {status}"
            
            # Multi-line label for better readability
            y_offset = y1 - 10
            for line in label.split(' - '):
                cv2.putText(frame, line, (x1, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
                y_offset -= 15
        
        return frame, detections
    except Exception as e:
        print(f"Detection error: {e}")
        return frame, []

def check_alerts(detections):
    global alerts
    import time
    
    for detection in detections:
        if detection['class_name'] == 'person':
            # Alert when NO head cover detected
            if not detection.get('has_headgear', False):
                alerts.append({
                    'type': 'no_headgear',
                    'timestamp': time.time(),
                    'bbox': detection['bbox'],
                    'confidence': detection['confidence'],
                    'message': '⚠️ SAFETY ALERT: Person without head protection detected'
                })
            
            # Chair movement alert
            if detection.get('with_moving_chair', False):
                alerts.append({
                    'type': 'chair_moved',
                    'timestamp': time.time(),
                    'bbox': detection['bbox'],
                    'confidence': detection['confidence'],
                    'message': '🪑 CHAIR MOVEMENT: Person moving chair detected'
                })
            
            # Zone violation check
            person_bbox = detection['bbox']
            person_center = ((person_bbox[0] + person_bbox[2]) // 2,
                           (person_bbox[1] + person_bbox[3]) // 2)
            
            for zone_id, zone_points in zones.items():
                if point_in_polygon(person_center, zone_points):
                    alerts.append({
                        'type': 'zone_violation',
                        'timestamp': time.time(),
                        'zone_id': zone_id,
                        'bbox': detection['bbox'],
                        'confidence': detection['confidence'],
                        'message': f'🚨 INTRUSION ALERT: Unauthorized access to restricted zone "{zone_id}"'
                    })
            
            # Walking detection alert (optional)
            if detection.get('is_walking', False) and not detection.get('with_moving_chair', False):
                alerts.append({
                    'type': 'person_walking',
                    'timestamp': time.time(),
                    'bbox': detection['bbox'],
                    'message': '🚶 MOVEMENT DETECTED: Person walking in monitored area'
                })
        
        elif detection['class_name'] == 'chair':
            # Alert for chair movement without person (suspicious)
            if detection.get('is_moving', False):
                # Check if any person is near this chair
                chair_with_person = False
                chair_center = ((detection['bbox'][0] + detection['bbox'][2]) // 2,
                              (detection['bbox'][1] + detection['bbox'][3]) // 2)
                
                for other_det in detections:
                    if other_det['class_name'] == 'person':
                        if detect_person_with_chair(other_det['bbox'], detection['bbox']):
                            chair_with_person = True
                            break
                
                if not chair_with_person:
                    alerts.append({
                        'type': 'chair_moved_alone',
                        'timestamp': time.time(),
                        'bbox': detection['bbox'],
                        'confidence': detection['confidence'],
                        'message': '🚨 SUSPICIOUS ACTIVITY: Chair moving without visible person nearby'
                    })
    
    # Keep last 100 alerts
    alerts = alerts[-100:]

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

@app.get("/api/status")
async def get_status():
    return {
        "pipeline_running": cap is not None and cap.isOpened(),
        "zones": list(zones.keys()),
        "recent_alerts": alerts[-10:] if alerts else []
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
                    # Run detection
                    frame_with_detections, detections = detect_objects(frame)
                    frame_with_detections = draw_zones(frame_with_detections)
                    
                    # Check alerts
                    if detections:
                        check_alerts(detections)
                    
                    # Resize for better performance and UI fit
                    height, width = frame_with_detections.shape[:2]
                    if width > 800:
                        scale = 800 / width
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        frame_with_detections = cv2.resize(frame_with_detections, (new_width, new_height))
                    
                    # Encode with good quality
                    _, buffer = cv2.imencode('.jpg', frame_with_detections, [cv2.IMWRITE_JPEG_QUALITY, 85])
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
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            'type': 'connection_status',
            'status': 'connected',
            'message': 'Live alerts system connected'
        }))
        
        while True:
            current_alert_count = len(alerts)
            if current_alert_count > last_alert_count:
                new_alerts = alerts[last_alert_count:]
                print(f"📢 Sending {len(new_alerts)} new alerts to frontend")
                
                await websocket.send_text(json.dumps({
                    'type': 'alerts',
                    'data': new_alerts
                }))
                last_alert_count = current_alert_count
            
            await asyncio.sleep(0.3)  # Check more frequently
    except WebSocketDisconnect:
        print("❌ Alerts WebSocket client disconnected")
        manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ Alerts WebSocket error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

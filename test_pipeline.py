#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.detection_pipeline import DetectionPipeline
import cv2
import time

def test_pipeline():
    """Test the detection pipeline"""
    print("Testing RTSP Object Detection Pipeline...")
    
    # Create pipeline
    pipeline = DetectionPipeline()
    
    try:
        print("Starting pipeline...")
        pipeline.start()
        
        print("Pipeline started. Processing frames for 10 seconds...")
        start_time = time.time()
        
        while time.time() - start_time < 10:
            frame = pipeline.get_current_frame_with_overlays()
            if frame is not None:
                # Display frame (optional - comment out if running headless)
                cv2.imshow('Detection Feed', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            time.sleep(0.1)
        
        print(f"Processed frames. Found {len(pipeline.alerts)} alerts.")
        
        # Print recent alerts
        for alert in pipeline.alerts[-5:]:
            print(f"Alert: {alert['type']} at {alert['timestamp']}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Stopping pipeline...")
        pipeline.stop()
        cv2.destroyAllWindows()
        print("Test completed.")

if __name__ == "__main__":
    test_pipeline()
